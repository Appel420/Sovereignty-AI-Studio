use policy_engine::{AuthorizationDecision, PolicyEngine};
use principal::{Capability, NetworkBoundary, Principal, PrincipalType};

fn principal() -> Principal {
    Principal {
        id: "analysis-runtime".into(),
        principal_type: PrincipalType::AiModel,
        role: "analysis".into(),
        runtime_version: "1.0".into(),
        capabilities: vec![Capability::Analyze],
        network_boundary: NetworkBoundary::LocalOnly,
        governance_owner: "owner".into(),
        policy_authority: "policy-root".into(),
        audit_enabled: true,
    }
}

#[test]
fn only_policy_engine_decides_capability_access() {
    assert_eq!(
        PolicyEngine::authorize(&principal(), Capability::Analyze),
        AuthorizationDecision::Allowed
    );
    assert_eq!(
        PolicyEngine::authorize(&principal(), Capability::Verify),
        AuthorizationDecision::Denied
    );
}

#[test]
fn external_access_requires_explicit_network_boundary() {
    assert_eq!(
        PolicyEngine::authorize_external(&principal(), Capability::Analyze),
        AuthorizationDecision::Denied
    );
}
