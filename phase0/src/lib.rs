use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum AccessDecision { Allow, Deny }

fn decision_code(decision: AccessDecision) -> &'static str {
    match decision { AccessDecision::Allow => "allow", AccessDecision::Deny => "deny" }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct EvaluationClock { now: u64 }
impl EvaluationClock {
    pub fn fixed(now: u64) -> Self { Self { now } }
    pub fn now(&self) -> u64 { self.now }
    pub fn system() -> Result<Self, AuthorizationError> {
        Ok(Self { now: SystemTime::now().duration_since(UNIX_EPOCH).map_err(|_| AuthorizationError::Clock)?.as_secs() })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Identity { pub id: String, pub branches: Vec<String> }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Grant {
    pub id: String,
    pub subject: String,
    pub resource: String,
    pub branch: String,
    pub granted_by: String,
    pub expires_at: Option<u64>,
    pub revoked: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum AuthorizationError { UnknownIdentity, UnknownResource, UnauthorizedIssuer, Expired, Revoked, Clock }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuditEvent {
    pub sequence: u64,
    pub grant_id: String,
    pub subject: String,
    pub resource: String,
    pub decision: String,
    pub reason: String,
    pub timestamp: u64,
    pub previous_hash: String,
    pub hash: String,
}

fn canonical_event_bytes(e: &AuditEvent) -> Vec<u8> {
    serde_json::to_vec(&(
        e.sequence, &e.grant_id, &e.subject, &e.resource, &e.decision,
        &e.reason, e.timestamp, &e.previous_hash
    )).expect("audit event serialization must be infallible")
}
fn event_hash(e: &AuditEvent) -> String {
    let mut h = Sha256::new(); h.update(canonical_event_bytes(e)); format!("{:x}", h.finalize())
}

#[derive(Default)]
pub struct AuditLedger { events: Vec<AuditEvent> }
impl AuditLedger {
    pub fn append(&mut self, mut event: AuditEvent) -> Result<(), &'static str> {
        let expected_seq = self.events.len() as u64 + 1;
        if event.sequence != expected_seq { return Err("invalid sequence"); }
        event.previous_hash = self.events.last().map(|x| x.hash.clone()).unwrap_or_default();
        event.hash = event_hash(&event);
        self.events.push(event); Ok(())
    }
    pub fn events(&self) -> &[AuditEvent] { &self.events }
    pub fn verify_chain(events: &[AuditEvent]) -> bool {
        let mut prev = String::new();
        for (i, e) in events.iter().enumerate() {
            if e.sequence != i as u64 + 1 || e.previous_hash != prev || e.hash != event_hash(e) { return false; }
            prev = e.hash.clone();
        }
        true
    }
    pub fn import_verified(events: Vec<AuditEvent>) -> Result<Self, &'static str> {
        if !Self::verify_chain(&events) { return Err("invalid audit chain"); }
        Ok(Self { events })
    }
}

pub struct AuthorizationEngine {
    identities: HashMap<String, Identity>,
    grants: HashMap<String, Grant>,
    resources: HashMap<String, String>,
}
impl AuthorizationEngine {
    pub fn new() -> Self { Self { identities: HashMap::new(), grants: HashMap::new(), resources: HashMap::new() } }
    pub fn add_identity(&mut self, identity: Identity) -> Result<(), &'static str> {
        if identity.id.is_empty() || self.identities.contains_key(&identity.id) { return Err("invalid or duplicate identity"); }
        self.identities.insert(identity.id.clone(), identity); Ok(())
    }
    pub fn add_resource(&mut self, resource: impl Into<String>, branch: impl Into<String>) -> Result<(), &'static str> {
        let resource = resource.into(); let branch = branch.into();
        if resource.is_empty() || branch.is_empty() || self.resources.contains_key(&resource) { return Err("invalid or duplicate resource"); }
        self.resources.insert(resource, branch); Ok(())
    }
    pub fn add_grant(&mut self, grant: Grant) -> Result<(), &'static str> {
        if self.grants.contains_key(&grant.id) || !self.identities.contains_key(&grant.subject) { return Err("invalid or duplicate grant"); }
        let branch = self.resources.get(&grant.resource).ok_or("unknown resource")?;
        let issuer = self.identities.get(&grant.granted_by).ok_or("unknown issuer")?;
        if branch != &grant.branch || !issuer.branches.iter().any(|b| b == branch) { return Err("issuer lacks grant authority"); }
        self.grants.insert(grant.id.clone(), grant); Ok(())
    }
    pub fn authorize(&self, grant_id: &str, clock: EvaluationClock) -> AccessDecision {
        self.authorize_checked(grant_id, clock).unwrap_or(AccessDecision::Deny)
    }
    pub fn authorize_checked(&self, grant_id: &str, clock: EvaluationClock) -> Result<AccessDecision, AuthorizationError> {
        let grant = self.grants.get(grant_id).ok_or(AuthorizationError::UnknownResource)?;
        if !self.identities.contains_key(&grant.subject) { return Err(AuthorizationError::UnknownIdentity); }
        if !self.resources.contains_key(&grant.resource) { return Err(AuthorizationError::UnknownResource); }
        if grant.revoked { return Err(AuthorizationError::Revoked); }
        if grant.expires_at.is_some_and(|t| clock.now() >= t) { return Err(AuthorizationError::Expired); }
        Ok(AccessDecision::Allow)
    }
    pub fn grant(&self, id: &str) -> Option<&Grant> { self.grants.get(id) }
}

pub fn make_audit_event(seq: u64, grant: &Grant, decision: AccessDecision, reason: impl Into<String>, timestamp: u64) -> AuditEvent {
    AuditEvent { sequence: seq, grant_id: grant.id.clone(), subject: grant.subject.clone(), resource: grant.resource.clone(), decision: decision_code(decision).to_string(), reason: reason.into(), timestamp, previous_hash: String::new(), hash: String::new() }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (AuthorizationEngine, Grant) {
        let mut e = AuthorizationEngine::new();
        e.add_identity(Identity { id: "owner".into(), branches: vec!["main".into()] }).unwrap();
        e.add_identity(Identity { id: "user".into(), branches: vec![] }).unwrap();
        e.add_resource("vault", "main").unwrap();
        let g = Grant { id: "g1".into(), subject: "user".into(), resource: "vault".into(), branch: "main".into(), granted_by: "owner".into(), expires_at: Some(100), revoked: false };
        e.add_grant(g.clone()).unwrap(); (e,g)
    }
    #[test] fn expiry_and_boundary() { let (e,_) = fixture(); assert_eq!(e.authorize("g1", EvaluationClock::fixed(99)), AccessDecision::Allow); assert_eq!(e.authorize("g1", EvaluationClock::fixed(100)), AccessDecision::Deny); }
    #[test] fn issuer_must_control_branch() { let mut e = AuthorizationEngine::new(); e.add_identity(Identity { id:"user".into(), branches:vec![] }).unwrap(); e.add_resource("r","main").unwrap(); assert!(e.add_grant(Grant{id:"g".into(),subject:"user".into(),resource:"r".into(),branch:"main".into(),granted_by:"user".into(),expires_at:None,revoked:false}).is_err()); }
    #[test] fn revocation_is_enforced() { let (mut e,g) = fixture(); let mut r=g.clone(); r.revoked=true; e.grants.insert(r.id.clone(),r); assert_eq!(e.authorize("g1",EvaluationClock::fixed(0)),AccessDecision::Deny); }
    #[test] fn canonical_audit_chain_is_stable() { let (_,g)=fixture(); let mut l=AuditLedger::default(); l.append(make_audit_event(1,&g,AccessDecision::Allow,"granted",1)).unwrap(); l.append(make_audit_event(2,&g,AccessDecision::Deny,"expired",100)).unwrap(); assert!(AuditLedger::verify_chain(l.events())); let mut tampered=l.events().to_vec(); tampered[1].decision="deny".into(); tampered[1].hash=String::from("bad"); assert!(!AuditLedger::verify_chain(&tampered)); assert_eq!(l.events()[0].decision,"allow"); }
    #[test] fn verified_import_is_tamper_boundary() { let (_,g)=fixture(); let mut l=AuditLedger::default(); l.append(make_audit_event(1,&g,AccessDecision::Allow,"granted",1)).unwrap(); assert!(AuditLedger::import_verified(l.events().to_vec()).is_ok()); }
}
