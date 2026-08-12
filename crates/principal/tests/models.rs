use principal::{Capability, NetworkBoundary, Principal, PrincipalType};

#[test]
fn principal_describes_identity_without_mutation_authority() {
    let principal = Principal {
        id: "analysis-runtime".into(),
        principal_type: PrincipalType::AiModel,
        role: "analysis".into(),
        runtime_version: "1.0".into(),
        capabilities: vec![Capability::Analyze],
        network_boundary: NetworkBoundary::LocalOnly,
        governance_owner: "owner".into(),
        policy_authority: "policy-root".into(),
        audit_enabled: true,
    };

    assert_eq!(principal.network_boundary, NetworkBoundary::LocalOnly);
    assert!(!principal.network_boundary.permits_external_network());
}

#[test]
fn capability_set_is_explicit() {
    let principal = Principal {
        id: "review-runtime".into(),
        principal_type: PrincipalType::Service,
        role: "review".into(),
        runtime_version: "1.0".into(),
        capabilities: vec![Capability::Verify],
        network_boundary: NetworkBoundary::Offline,
        governance_owner: "owner".into(),
        policy_authority: "policy-root".into(),
        audit_enabled: true,
    };

    assert!(principal.has_capability(Capability::Verify));
    assert!(!principal.has_capability(Capability::GenerateOutput));
}
