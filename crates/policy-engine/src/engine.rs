use principal::{Capability, Principal};

use crate::decision::AuthorizationDecision;

pub struct PolicyEngine;

impl PolicyEngine {
    /// The sole authorization entry point for this bounded core.
    pub fn authorize(principal: &Principal, capability: Capability) -> AuthorizationDecision {
        if principal.has_capability(capability) {
            AuthorizationDecision::Allowed
        } else {
            AuthorizationDecision::Denied
        }
    }

    /// External network access requires both an explicit boundary and the
    /// capability requested by the caller. This remains policy-owned.
    pub fn authorize_external(
        principal: &Principal,
        capability: Capability,
    ) -> AuthorizationDecision {
        if !principal.network_boundary.permits_external_network() {
            return AuthorizationDecision::Denied;
        }
        Self::authorize(principal, capability)
    }
}
