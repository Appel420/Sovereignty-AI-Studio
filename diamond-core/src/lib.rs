#![forbid(unsafe_code)]

pub mod authority;
pub mod hash;
pub mod identity;
pub mod provenance;
pub mod store;
pub mod transition;
pub mod types;
pub mod window;

pub use authority::{AccessRequest, Capability, Decision, AccessError};
pub use identity::{MemoryObject, ObjectMeta};
pub use provenance::Provenance;
pub use store::ObjectStore;
pub use transition::{TransitionRecord, ScarEvent, ScarSnapshot};
pub use types::{AuthorityState, Hash, ObjectId, CapabilityId, PolicyId, SubjectId, TransitionId, Operation};
pub use window::MemoryWindow;

pub fn now_seconds() -> u64 { std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs() }

#[cfg(test)]
mod tests;
