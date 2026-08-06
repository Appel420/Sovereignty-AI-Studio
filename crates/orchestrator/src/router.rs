use policy_engine::AuthorizationDecision;

pub struct LocalOrchestrator;

impl LocalOrchestrator {
    /// Routes a decision produced by PolicyEngine. It cannot create or alter
    /// authorization and has no access to principals or policy storage.
    pub const fn route(decision: AuthorizationDecision) -> &'static str {
        match decision {
            AuthorizationDecision::Allowed => "dispatch",
            AuthorizationDecision::Denied => "reject",
            AuthorizationDecision::HumanApprovalRequired => "escalate",
        }
    }
}
