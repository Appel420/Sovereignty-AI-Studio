use crate::boundary::NetworkBoundary;
use crate::capabilities::Capability;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PrincipalType {
    Human,
    AiModel,
    Service,
    Device,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Principal {
    pub id: String,
    pub principal_type: PrincipalType,
    pub role: String,
    pub runtime_version: String,
    pub capabilities: Vec<Capability>,
    pub network_boundary: NetworkBoundary,
    pub governance_owner: String,
    pub policy_authority: String,
    pub audit_enabled: bool,
}

impl Principal {
    pub fn has_capability(&self, capability: Capability) -> bool {
        self.capabilities.contains(&capability)
    }
}
