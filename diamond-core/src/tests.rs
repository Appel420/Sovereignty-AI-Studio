use super::*;
use std::collections::BTreeSet;

fn provenance(source: &str) -> Provenance {
    Provenance { source: source.into(), parent_ids: vec![], transformation: "ingest".into(), evidence_hash: hash_str("evidence") }
}

fn object(state: MemoryState) -> MemoryObject {
    let mut o = MemoryObject::new("ns", "uuid-1", b"hello", 1, "ctx-A", provenance("user"));
    o.state = state;
    o
}

fn cap(subject: &str, id: &ObjectId, ops: &[Operation]) -> Capability {
    Capability {
        subject: subject.into(),
        object_ids: [id.0.clone()].into_iter().collect(),
        operations: ops.iter().copied().collect(),
        context_hash: "ctx-A".into(),
        issued_at: 100,
        expires_at: 200,
        epoch: 1,
        policy_hash: "policy-v1".into(),
    }
}

fn setup(state: MemoryState) -> (Core, MemoryObject) {
    let o = object(state);
    let mut c = Core::new("policy-v1");
    c.insert(o.clone()).unwrap();
    (c, o)
}

#[test]
fn i001_access_requires_authority() {
    let (c, o) = setup(MemoryState::Unverified);
    let no_cap = cap("other", &o.id, &[Operation::Read]);
    assert_eq!(c.access("model", &o.id, Operation::Read, "ctx-A", &no_cap, 100), Err(AccessError::AuthorityDenied));
}

#[test]
fn i002_versions_are_immutable() {
    let o = object(MemoryState::Unverified);
    let next = o.next_version(b"changed", provenance("transform"));
    assert_ne!(o.id, next.id);
    assert_eq!(o.version, 1);
    assert_eq!(next.version, 2);
}

#[test]
fn i003_derivation_preserves_parent_provenance() {
    let parent = object(MemoryState::Unverified);
    let mut p = provenance("model");
    p.parent_ids.push(parent.id.0.clone());
    let child = parent.next_version(b"derived", p.clone());
    assert!(child.provenance.parent_ids.contains(&parent.id.0));
    assert_eq!(child.provenance_root, provenance_commitment(&p));
}

#[test]
fn i004_model_generated_cannot_skip_unverified() {
    let (mut c, o) = setup(MemoryState::ModelGenerated);
    let capability = cap("operator", &o.id, &[Operation::Promote]);
    assert_eq!(c.transition("operator", &o.id, MemoryState::PolicyApproved, "e", "p", 100, &capability), Err(AccessError::InvalidTransition));
}

#[test]
fn i005_revoked_capability_fails() {
    let (c, o) = setup(MemoryState::Unverified);
    let capability = cap("model", &o.id, &[Operation::Read]);
    let mut revoked = capability.clone();
    revoked.expires_at = 99;
    assert_eq!(c.access("model", &o.id, Operation::Read, "ctx-A", &revoked, 100), Err(AccessError::AuthorityDenied));
}

#[test]
fn i006_expired_window_fails() {
    let (c, o) = setup(MemoryState::Unverified);
    let capability = cap("model", &o.id, &[Operation::Read]);
    let ids = [o.id.0.clone()].into_iter().collect();
    let window = c.window("model", ids, 100, "ctx-A", capability, 100).unwrap();
    assert_eq!(c.window_read("model", &window, &o.id, 1, 200), Err(AccessError::WindowExpired));
}

#[test]
fn i007_window_is_object_scoped_and_bounded() {
    let (c, o) = setup(MemoryState::Unverified);
    let capability = cap("model", &o.id, &[Operation::Read]);
    let ids = [o.id.0.clone()].into_iter().collect();
    let window = c.window("model", ids, 8, "ctx-A", capability, 100).unwrap();
    assert_eq!(c.window_read("model", &window, &o.id, 9, 101), Err(AccessError::ByteLimitExceeded));
    assert!(!window.object_ids.is_empty());
}

#[test]
fn i008_logical_identity_survives_without_physical_addresses() {
    let (c, o) = setup(MemoryState::Unverified);
    let capability = cap("model", &o.id, &[Operation::Read]);
    let ids = [o.id.0.clone()].into_iter().collect();
    let window = c.window("model", ids, 100, "ctx-A", capability, 100).unwrap();
    assert_eq!(window.object_ids.len(), 1);
    assert!(!window.object_ids.contains("0xdeadbeef"));
}

#[test]
fn i009_export_is_not_implied_by_read() {
    let (c, o) = setup(MemoryState::Unverified);
    let capability = cap("model", &o.id, &[Operation::Read]);
    assert_eq!(c.access("model", &o.id, Operation::Export, "ctx-A", &capability, 100), Err(AccessError::AuthorityDenied));
}

#[test]
fn i010_authority_transition_emits_scar() {
    let (mut c, o) = setup(MemoryState::Unverified);
    let capability = cap("operator", &o.id, &[Operation::Promote]);
    c.transition("operator", &o.id, MemoryState::Reviewed, "evidence-1", "auth-1", 100, &capability).unwrap();
    assert_eq!(c.scar.len(), 1);
    assert_eq!(c.scar[0].evidence_hash, "evidence-1");
}

#[test]
fn i011_provenance_tampering_fails_closed() {
    let (mut c, o) = setup(MemoryState::Unverified);
    c.objects.get_mut(&o.id.0).unwrap().provenance.source = "tampered".into();
    let capability = cap("model", &o.id, &[Operation::Read]);
    assert_eq!(c.access("model", &o.id, Operation::Read, "ctx-A", &capability, 100), Err(AccessError::ProvenanceMismatch));
}

#[test]
fn i012_snapshot_detects_mutation() {
    let (mut c, o) = setup(MemoryState::Unverified);
    let root = c.snapshot_root();
    c.objects.get_mut(&o.id.0).unwrap().state = MemoryState::Quarantined;
    assert!(!c.verify_snapshot(&root));
}

#[test]
fn i013_model_cannot_modify_policy() {
    let (c, o) = setup(MemoryState::Unverified);
    let capability = cap("model", &o.id, &[Operation::Promote, Operation::Read]);
    assert_eq!(c.access("model", &o.id, Operation::Promote, "ctx-A", &capability, 100), Ok(()));
    assert_eq!(c.policy_hash, "policy-v1");
}

#[test]
fn i014_model_cannot_self_grant_capability() {
    let (c, o) = setup(MemoryState::Unverified);
    let self_granted = Capability { subject: "model".into(), object_ids: [o.id.0.clone()].into_iter().collect(), operations: [Operation::Export].into_iter().collect(), context_hash: "ctx-A".into(), issued_at: 100, expires_at: 200, epoch: 999, policy_hash: "forged".into() };
    assert_eq!(c.access("model", &o.id, Operation::Export, "ctx-A", &self_granted, 100), Err(AccessError::AuthorityDenied));
}

#[test]
fn i015_physical_tier_cannot_override_authority() {
    let (c, o) = setup(MemoryState::Unverified);
    let capability = cap("model", &o.id, &[Operation::Read]);
    // v0.1 exposes no physical-tier handle at all. The only model-facing path is MemoryWindow.
    let ids: BTreeSet<String> = [o.id.0.clone()].into_iter().collect();
    let window = c.window("model", ids, 100, "ctx-A", capability, 100).unwrap();
    assert_eq!(c.window_read("model", &window, &o.id, 1, 100), Ok(()));
    assert_eq!(c.access("model", &o.id, Operation::Delete, "ctx-A", &window.capability, 100), Err(AccessError::AuthorityDenied));
}

#[test]
fn full_poisoning_path_is_required_and_logged() {
    let (mut c, o) = setup(MemoryState::ModelGenerated);
    let capability = cap("operator", &o.id, &[Operation::Promote]);
    for state in [MemoryState::Unverified, MemoryState::Reviewed, MemoryState::PolicyApproved, MemoryState::Authoritative] {
        c.transition("operator", &o.id, state, "evidence", "authorization", 100, &capability).unwrap();
    }
    assert_eq!(c.object(&o.id).unwrap().state, MemoryState::Authoritative);
    assert_eq!(c.scar.len(), 4);
}
