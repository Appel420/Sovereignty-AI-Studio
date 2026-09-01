//! Diamond Lattice 5D Core v0.1.
//! Contract-first, in-memory reference implementation. Physical memory is deliberately absent.

use blake3::Hasher;
use std::collections::{BTreeMap, BTreeSet};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Operation { Read, Create, Derive, Transform, Promote, Export, Share, Revoke, Delete }

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum MemoryState { Authoritative, Verified, UserProvided, Observed, ModelGenerated, Unverified, Reviewed, PolicyApproved, Quarantined, Revoked }

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Provenance { pub source: String, pub parent_ids: Vec<String>, pub transformation: String, pub evidence_hash: String }

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObjectId(pub String);

impl ObjectId {
    pub fn derive(namespace: &str, uuid: &str, content_hash: &str, version: u64, provenance_root: &str) -> Self {
        let mut h = Hasher::new();
        for field in [namespace, uuid, content_hash, &version.to_string(), provenance_root] {
            h.update(&(field.len() as u64).to_be_bytes());
            h.update(field.as_bytes());
        }
        Self(h.finalize().to_hex().to_string())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MemoryObject {
    pub id: ObjectId,
    pub namespace: String,
    pub uuid: String,
    pub content_hash: String,
    pub version: u64,
    pub provenance_root: String,
    pub context_hash: String,
    pub state: MemoryState,
    pub provenance: Provenance,
}

impl MemoryObject {
    pub fn new(namespace: &str, uuid: &str, content: &[u8], version: u64, context_hash: &str, provenance: Provenance) -> Self {
        let content_hash = hash_bytes(content);
        let provenance_root = provenance_commitment(&provenance);
        let id = ObjectId::derive(namespace, uuid, &content_hash, version, &provenance_root);
        Self { id, namespace: namespace.into(), uuid: uuid.into(), content_hash, version, provenance_root, context_hash: context_hash.into(), state: MemoryState::Unverified, provenance }
    }

    pub fn next_version(&self, content: &[u8], provenance: Provenance) -> Self {
        Self::new(&self.namespace, &self.uuid, content, self.version + 1, &self.context_hash, provenance)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capability {
    pub subject: String,
    pub object_ids: BTreeSet<String>,
    pub operations: BTreeSet<Operation>,
    pub context_hash: String,
    pub issued_at: u64,
    pub expires_at: u64,
    pub epoch: u64,
    pub policy_hash: String,
}

impl Capability {
    pub fn valid_at(&self, now: u64, subject: &str, object: &ObjectId, operation: Operation, context_hash: &str, epoch: u64, policy_hash: &str) -> bool {
        self.subject == subject && self.object_ids.contains(&object.0) && self.operations.contains(&operation)
            && self.context_hash == context_hash && now >= self.issued_at && now < self.expires_at
            && self.epoch == epoch && self.policy_hash == policy_hash
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MemoryWindow {
    pub object_ids: BTreeSet<String>,
    pub byte_limit: u64,
    pub context_hash: String,
    pub capability: Capability,
    pub expires_at: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScarEvent {
    pub event: String,
    pub subject: String,
    pub object_id: String,
    pub from: MemoryState,
    pub to: MemoryState,
    pub evidence_hash: String,
    pub authorization_proof: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AccessError {
    IdentityMismatch, TemporalMismatch, ContextMismatch, ProvenanceMismatch, AuthorityDenied, WindowExpired, ByteLimitExceeded, InvalidTransition,
}

pub struct Core {
    objects: BTreeMap<String, MemoryObject>,
    pub epoch: u64,
    pub policy_hash: String,
    pub scar: Vec<ScarEvent>,
}

impl Core {
    pub fn new(policy_hash: &str) -> Self { Self { objects: BTreeMap::new(), epoch: 1, policy_hash: policy_hash.into(), scar: Vec::new() } }

    pub fn insert(&mut self, object: MemoryObject) -> Result<(), AccessError> {
        if self.objects.contains_key(&object.id.0) { return Err(AccessError::IdentityMismatch); }
        self.objects.insert(object.id.0.clone(), object);
        Ok(())
    }

    pub fn object(&self, id: &ObjectId) -> Option<&MemoryObject> { self.objects.get(&id.0) }

    pub fn access(&self, subject: &str, object: &ObjectId, operation: Operation, context_hash: &str, capability: &Capability, now: u64) -> Result<(), AccessError> {
        let o = self.objects.get(&object.0).ok_or(AccessError::IdentityMismatch)?;
        if o.id != *object { return Err(AccessError::IdentityMismatch); }
        if o.version == 0 { return Err(AccessError::TemporalMismatch); }
        if o.context_hash != context_hash { return Err(AccessError::ContextMismatch); }
        if o.provenance_root != provenance_commitment(&o.provenance) { return Err(AccessError::ProvenanceMismatch); }
        if !capability.valid_at(now, subject, object, operation, context_hash, self.epoch, &self.policy_hash) { return Err(AccessError::AuthorityDenied); }
        Ok(())
    }

    pub fn window(&self, subject: &str, ids: BTreeSet<String>, byte_limit: u64, context_hash: &str, capability: Capability, now: u64) -> Result<MemoryWindow, AccessError> {
        if now >= capability.expires_at || now >= capability.expires_at { return Err(AccessError::WindowExpired); }
        for id in &ids {
            let object = self.objects.get(id).ok_or(AccessError::IdentityMismatch)?;
            self.access(subject, &object.id, Operation::Read, context_hash, &capability, now)?;
        }
        Ok(MemoryWindow { object_ids: ids, byte_limit, context_hash: context_hash.into(), expires_at: capability.expires_at, capability })
    }

    pub fn window_read(&self, subject: &str, window: &MemoryWindow, id: &ObjectId, bytes: u64, now: u64) -> Result<(), AccessError> {
        if now >= window.expires_at { return Err(AccessError::WindowExpired); }
        if !window.object_ids.contains(&id.0) { return Err(AccessError::AuthorityDenied); }
        if bytes > window.byte_limit { return Err(AccessError::ByteLimitExceeded); }
        self.access(subject, id, Operation::Read, &window.context_hash, &window.capability, now)
    }

    pub fn transition(&mut self, subject: &str, id: &ObjectId, to: MemoryState, evidence_hash: &str, authorization_proof: &str, now: u64, capability: &Capability) -> Result<(), AccessError> {
        let object = self.objects.get(id).ok_or(AccessError::IdentityMismatch)?;
        let from = object.state;
        let allowed = matches!((from, to),
            (MemoryState::ModelGenerated, MemoryState::Unverified) |
            (MemoryState::Unverified, MemoryState::Reviewed) |
            (MemoryState::Reviewed, MemoryState::PolicyApproved) |
            (MemoryState::PolicyApproved, MemoryState::Authoritative) |
            (MemoryState::Authoritative, MemoryState::Revoked));
        if !allowed { return Err(AccessError::InvalidTransition); }
        self.access(subject, id, Operation::Promote, &object.context_hash, capability, now)?;
        let object = self.objects.get_mut(&id.0).unwrap();
        object.state = to;
        self.scar.push(ScarEvent { event: "MEMORY_STATE_TRANSITION".into(), subject: subject.into(), object_id: id.0.clone(), from, to, evidence_hash: evidence_hash.into(), authorization_proof: authorization_proof.into() });
        Ok(())
    }

    pub fn snapshot_root(&self) -> String {
        let mut level: Vec<String> = self.objects.values().map(|o| hash_str(&format!("{}:{}:{}:{}:{}", o.id.0, o.version, o.context_hash, o.provenance_root, o.state as u8))).collect();
        level.sort();
        if level.is_empty() { return hash_str(""); }
        while level.len() > 1 {
            level = level.chunks(2).map(|pair| if pair.len() == 2 { hash_str(&(pair[0].clone() + &pair[1])) } else { hash_str(&(pair[0].clone() + &pair[0])) }).collect();
        }
        level.remove(0)
    }

    pub fn verify_snapshot(&self, expected: &str) -> bool { self.snapshot_root() == expected }
}

pub fn now_seconds() -> u64 { SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or(Duration::ZERO).as_secs() }
pub fn hash_bytes(data: &[u8]) -> String { blake3::hash(data).to_hex().to_string() }
pub fn hash_str(data: &str) -> String { hash_bytes(data.as_bytes()) }
pub fn provenance_commitment(p: &Provenance) -> String { hash_str(&format!("{}|{}|{}|{}", p.source, p.parent_ids.join(","), p.transformation, p.evidence_hash)) }

#[cfg(test)]
mod tests;
