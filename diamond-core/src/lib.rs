//! Diamond Lattice 5D Core v0.1.
//! Contract-first reference implementation. Physical memory is deliberately absent.

use blake3::Hasher;
use std::collections::{BTreeMap, BTreeSet};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub type Hash = [u8; 32];
pub type ObjectId = Hash; pub type CapabilityId = Hash; pub type PolicyId = Hash; pub type SubjectId = Hash; pub type TransitionId = Hash;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)] pub enum AuthorityState { ModelGenerated, Unverified, Reviewed, PolicyApproved, Authoritative }
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)] pub enum Operation { Read, Create, Derive, Transform, Promote, Export, Share, Revoke, Delete }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Decision { Allow, Deny, Audit }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum AccessStage { Identity, Temporal, Context, Provenance, Authority }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum AccessError { IdentityMismatch, TemporalMismatch, ContextMismatch, ProvenanceMismatch, AuthorityDenied, WindowExpired, ByteLimitExceeded, InvalidTransition, InvalidCapability }

#[derive(Clone, Debug, PartialEq, Eq)] pub struct Provenance { pub parent_object_ids: Vec<ObjectId>, pub evidence_hash: Hash, pub source_system: String }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct ObjectMeta {
    pub namespace: String, pub object_uuid: String, pub content_hash: Hash, pub version: u64, pub provenance_root: Hash,
    pub context_hash: Hash, pub temporal_epoch: u64, pub valid_from: u64, pub valid_until: u64,
}
#[derive(Clone, Debug, PartialEq, Eq)] pub struct MemoryObject { pub id: ObjectId, pub meta: ObjectMeta, pub provenance: Provenance, pub authority_state: AuthorityState, pub payload: Vec<u8> }
impl MemoryObject {
    pub fn new(namespace: &str, uuid: &str, content: &[u8], version: u64, context_hash: Hash, epoch: u64, provenance: Provenance) -> Self {
        let content_hash=hash_bytes(content); let provenance_root=provenance_commitment(&provenance); let id=derive_object_id(namespace,uuid,content_hash,version,provenance_root);
        Self { id, meta:ObjectMeta { namespace:namespace.into(), object_uuid:uuid.into(), content_hash, version, provenance_root, context_hash, temporal_epoch:epoch, valid_from:0, valid_until:u64::MAX }, provenance, authority_state:AuthorityState::Unverified, payload:content.to_vec() }
    }
    pub fn canonical_id(&self)->ObjectId { derive_object_id(&self.meta.namespace,&self.meta.object_uuid,self.meta.content_hash,self.meta.version,self.meta.provenance_root) }
    pub fn next_version(&self, content:&[u8], provenance:Provenance, epoch:u64)->Self { Self::new(&self.meta.namespace,&self.meta.object_uuid,content,self.meta.version+1,self.meta.context_hash,epoch,provenance) }
}

#[derive(Clone, Debug, PartialEq, Eq)] pub struct Capability { id:CapabilityId, subject:SubjectId, object_scope:BTreeSet<ObjectId>, allowed_operations:BTreeSet<Operation>, context_hash:Hash, issued_at:u64, expiration:u64, epoch:u64, policy_hash:PolicyId, revoked:bool }
impl Capability { pub fn id(&self)->CapabilityId{self.id} pub fn expiration(&self)->u64{self.expiration} pub fn subject(&self)->SubjectId{self.subject} pub fn revoked(&self)->bool{self.revoked}
    fn valid_at(&self,req:&AccessRequest,now:u64,policy:PolicyId,epoch:u64)->bool { !self.revoked&&self.subject==req.subject&&self.object_scope.contains(&req.object_id)&&self.allowed_operations.contains(&req.operation)&&self.context_hash==req.context_hash&&self.issued_at<=now&&now<self.expiration&&self.epoch==epoch&&self.policy_hash==policy }
}
#[derive(Clone, Debug, PartialEq, Eq)] pub struct AccessRequest { pub subject:SubjectId,pub object_id:ObjectId,pub operation:Operation,pub context_hash:Hash,pub epoch:u64 }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct MemoryWindow { pub window_id:Hash,pub object_ids:BTreeSet<ObjectId>,pub maximum_bytes:u64,pub context_hash:Hash,capability_id:CapabilityId,pub expiration:u64 }
impl MemoryWindow{pub fn capability_id(&self)->CapabilityId{self.capability_id}}
#[derive(Clone, Debug, PartialEq, Eq)] pub struct TransitionRecord { pub transition_id:TransitionId,pub subject:SubjectId,pub policy_id:PolicyId,pub source_object:ObjectId,pub destination_object:ObjectId,pub timestamp:u64,pub previous_state:AuthorityState,pub new_state:AuthorityState,pub evidence_hash:Hash,pub authorization_proof:Hash }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct ScarEvent{pub transition:TransitionRecord}
#[derive(Clone, Debug, PartialEq, Eq)] pub struct ScarSnapshot{pub root:Hash,pub epoch:u64}

pub struct Core { objects:BTreeMap<ObjectId,MemoryObject>, capabilities:BTreeMap<CapabilityId,Capability>, epoch:u64, policy_hash:PolicyId, pub scar:Vec<ScarEvent>, pub scar_snapshots:Vec<ScarSnapshot> }
impl Core {
    pub fn new(policy_hash:PolicyId)->Self{Self{objects:BTreeMap::new(),capabilities:BTreeMap::new(),epoch:1,policy_hash,scar:Vec::new(),scar_snapshots:Vec::new()}}
    pub fn epoch(&self)->u64{self.epoch} pub fn policy_hash(&self)->PolicyId{self.policy_hash}
    pub fn insert(&mut self,object:MemoryObject)->Result<(),AccessError>{
        if object.meta.version==0||object.id!=object.canonical_id()||object.meta.provenance_root!=provenance_commitment(&object.provenance){return Err(AccessError::IdentityMismatch)}
        if object.meta.temporal_epoch!=self.epoch||self.objects.contains_key(&object.id){return Err(AccessError::IdentityMismatch)}
        if object.provenance.parent_object_ids.iter().any(|p|!self.objects.contains_key(p)){return Err(AccessError::ProvenanceMismatch)}
        self.objects.insert(object.id,object);Ok(())
    }
    pub fn object(&self,id:&ObjectId)->Option<&MemoryObject>{self.objects.get(id)}
    pub fn issue_capability(&mut self,subject:SubjectId,object_scope:BTreeSet<ObjectId>,operations:BTreeSet<Operation>,context_hash:Hash,issued_at:u64,ttl_seconds:u64)->CapabilityId{
        let expiration=issued_at.saturating_add(ttl_seconds);let id=capability_id(subject,&object_scope,&operations,context_hash,issued_at,expiration,self.epoch,self.policy_hash);
        self.capabilities.insert(id,Capability{id,subject,object_scope,allowed_operations:operations,context_hash,issued_at,expiration,epoch:self.epoch,policy_hash:self.policy_hash,revoked:false});id
    }
    pub fn revoke_capability(&mut self,subject:SubjectId,id:CapabilityId)->Result<(),AccessError>{let c=self.capabilities.get_mut(&id).ok_or(AccessError::InvalidCapability)?;if c.subject!=subject{return Err(AccessError::AuthorityDenied)}c.revoked=true;Ok(())}
    pub fn access(&self,req:&AccessRequest,capability_id:CapabilityId,now:u64)->Result<Decision,AccessError>{
        let o=self.objects.get(&req.object_id).ok_or(AccessError::IdentityMismatch)?;
        if o.id!=req.object_id||o.id!=o.canonical_id(){return Err(AccessError::IdentityMismatch)}
        if req.epoch!=self.epoch||o.meta.temporal_epoch!=req.epoch||req.epoch==0||now<o.meta.valid_from||now>o.meta.valid_until{return Err(AccessError::TemporalMismatch)}
        if o.meta.context_hash!=req.context_hash{return Err(AccessError::ContextMismatch)}
        if o.meta.provenance_root!=provenance_commitment(&o.provenance)||o.provenance.parent_object_ids.iter().any(|p|!self.objects.contains_key(p)){return Err(AccessError::ProvenanceMismatch)}
        let cap=self.capabilities.get(&capability_id).ok_or(AccessError::InvalidCapability)?;if !cap.valid_at(req,now,self.policy_hash,self.epoch){return Err(AccessError::AuthorityDenied)}
        if req.operation==Operation::Export{return Err(AccessError::AuthorityDenied)}
        Ok(Decision::Allow)
    }
    pub fn window(&self,subject:SubjectId,ids:BTreeSet<ObjectId>,maximum_bytes:u64,context_hash:Hash,capability_id:CapabilityId,now:u64)->Result<MemoryWindow,AccessError>{
        let cap=self.capabilities.get(&capability_id).ok_or(AccessError::InvalidCapability)?;if cap.subject!=subject||now>=cap.expiration{return Err(AccessError::WindowExpired)}
        for id in &ids{let req=AccessRequest{subject,object_id:*id,operation:Operation::Read,context_hash,epoch:self.epoch};self.access(&req,capability_id,now)?;}
        Ok(MemoryWindow{window_id:window_id(&ids,maximum_bytes,context_hash,capability_id,cap.expiration),object_ids:ids,maximum_bytes,context_hash,capability_id,expiration:cap.expiration})
    }
    pub fn window_read(&self,subject:SubjectId,window:&MemoryWindow,id:ObjectId,bytes:u64,now:u64)->Result<Decision,AccessError>{
        if now>=window.expiration{return Err(AccessError::WindowExpired)} if !window.object_ids.contains(&id){return Err(AccessError::AuthorityDenied)} if bytes>window.maximum_bytes{return Err(AccessError::ByteLimitExceeded)}
        self.access(&AccessRequest{subject,object_id:id,operation:Operation::Read,context_hash:window.context_hash,epoch:self.epoch},window.capability_id,now)
    }
    pub fn transition(&mut self,subject:SubjectId,id:ObjectId,to:AuthorityState,evidence_hash:Hash,authorization_proof:Hash,now:u64,capability_id:CapabilityId)->Result<ObjectId,AccessError>{
        let current=self.objects.get(&id).ok_or(AccessError::IdentityMismatch)?.clone();let from=current.authority_state;
        if !matches!((from,to),(AuthorityState::ModelGenerated,AuthorityState::Unverified)|(AuthorityState::Unverified,AuthorityState::Reviewed)|(AuthorityState::Reviewed,AuthorityState::PolicyApproved)|(AuthorityState::PolicyApproved,AuthorityState::Authoritative)){return Err(AccessError::InvalidTransition)}
        self.access(&AccessRequest{subject,object_id:id,operation:Operation::Promote,context_hash:current.meta.context_hash,epoch:self.epoch},capability_id,now)?;
        let next=current.next_version(&current.payload,Provenance{parent_object_ids:vec![id],evidence_hash,source_system:"diamond-core:authority-transition".into()},self.epoch);let destination=next.id;
        self.insert(MemoryObject{authority_state:to,..next})?;
        let transition_id=derive_transition_id(subject,self.policy_hash,id,destination,now,from,to,evidence_hash,authorization_proof);
        self.scar.push(ScarEvent{transition:TransitionRecord{transition_id,subject,policy_id:self.policy_hash,source_object:id,destination_object:destination,timestamp:now,previous_state:from,new_state:to,evidence_hash,authorization_proof}});Ok(destination)
    }
    pub fn snapshot_root(&self)->Hash{merkle_root(self.objects.values().map(object_commitment).collect())}
    pub fn record_snapshot(&mut self)->Hash{let root=self.snapshot_root();self.scar_snapshots.push(ScarSnapshot{root,epoch:self.epoch});root}
    pub fn verify_snapshot(&self,expected:Hash)->bool{self.snapshot_root()==expected}
}

fn derive_object_id(namespace:&str,uuid:&str,content_hash:Hash,version:u64,provenance_root:Hash)->ObjectId{let mut h=Hasher::new();put_bytes(&mut h,namespace.as_bytes());put_bytes(&mut h,uuid.as_bytes());h.update(&content_hash);h.update(&version.to_be_bytes());h.update(&provenance_root);*h.finalize().as_bytes()}
fn capability_id(subject:SubjectId,ids:&BTreeSet<ObjectId>,ops:&BTreeSet<Operation>,context:Hash,issued:u64,expires:u64,epoch:u64,policy:PolicyId)->CapabilityId{let mut h=Hasher::new();h.update(&subject);for id in ids{h.update(id)}for op in ops{h.update(&[*op as u8])}h.update(&context);h.update(&issued.to_be_bytes());h.update(&expires.to_be_bytes());h.update(&epoch.to_be_bytes());h.update(&policy);*h.finalize().as_bytes()}
fn window_id(ids:&BTreeSet<ObjectId>,bytes:u64,context:Hash,cap:CapabilityId,expiration:u64)->Hash{let mut h=Hasher::new();for id in ids{h.update(id)}h.update(&bytes.to_be_bytes());h.update(&context);h.update(&cap);h.update(&expiration.to_be_bytes());*h.finalize().as_bytes()}
fn derive_transition_id(subject:SubjectId,policy:PolicyId,source:ObjectId,destination:ObjectId,timestamp:u64,from:AuthorityState,to:AuthorityState,evidence:Hash,proof:Hash)->TransitionId{let mut h=Hasher::new();h.update(&subject);h.update(&policy);h.update(&source);h.update(&destination);h.update(&timestamp.to_be_bytes());h.update(&[from as u8,to as u8]);h.update(&evidence);h.update(&proof);*h.finalize().as_bytes()}
fn object_commitment(o:&MemoryObject)->Hash{let mut h=Hasher::new();h.update(&o.id);h.update(&o.meta.version.to_be_bytes());h.update(&o.meta.provenance_root);h.update(&o.meta.context_hash);h.update(&[o.authority_state as u8]);*h.finalize().as_bytes()}
fn put_bytes(h:&mut Hasher,b:&[u8]){h.update(&(b.len() as u64).to_be_bytes());h.update(b)}
pub fn hash_bytes(data:&[u8])->Hash{*blake3::hash(data).as_bytes()}
pub fn provenance_commitment(p:&Provenance)->Hash{let mut h=Hasher::new();put_bytes(&mut h,p.source_system.as_bytes());h.update(&(p.parent_object_ids.len() as u64).to_be_bytes());for id in &p.parent_object_ids{h.update(id)}h.update(&p.evidence_hash);*h.finalize().as_bytes()}
pub fn merkle_root(mut leaves:Vec<Hash>)->Hash{if leaves.is_empty(){return hash_bytes(b"")}leaves.sort();while leaves.len()>1{let mut next=Vec::with_capacity((leaves.len()+1)/2);for pair in leaves.chunks(2){let right=if pair.len()==2{pair[1]}else{pair[0]};let mut h=Hasher::new();h.update(&pair[0]);h.update(&right);next.push(*h.finalize().as_bytes())}leaves=next}leaves[0]}
pub fn now_seconds()->u64{SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or(Duration::ZERO).as_secs()}

#[cfg(test)] mod tests;
