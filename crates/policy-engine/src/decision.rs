#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuthorizationDecision {
    Allowed,
    Denied,
    HumanApprovalRequired,
}

impl AuthorizationDecision {
    pub const fn is_allowed(self) -> bool {
        matches!(self, Self::Allowed)
    }
}
