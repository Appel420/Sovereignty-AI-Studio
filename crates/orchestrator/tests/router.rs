use orchestrator::LocalOrchestrator;
use policy_engine::AuthorizationDecision;

#[test]
fn orchestrator_routes_allowed_decision() {
    assert_eq!(LocalOrchestrator::route(AuthorizationDecision::Allowed), "dispatch");
}

#[test]
fn orchestrator_cannot_escalate_denied_decision() {
    assert_eq!(LocalOrchestrator::route(AuthorizationDecision::Denied), "reject");
}

#[test]
fn orchestrator_preserves_human_approval_boundary() {
    assert_eq!(
        LocalOrchestrator::route(AuthorizationDecision::HumanApprovalRequired),
        "escalate"
    );
}
