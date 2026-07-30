"""Focused contract tests for GateOne and local MCP policy."""
from __future__ import annotations

from backend.gateone.gateone_policy_adapter import GateOnePolicyAdapter
from backend.mcp.mcp_policy_adapter import MCPPolicyAdapter
from backend.mcp.policy_engine import PolicyDecision, PolicyEngine


POLICY = {
    "version": "1.0.0",
    "provider_policy": {"allow": ["openai"], "deny": ["gemini"]},
    "bridge_requirements": {
        "trust_boundary": "local-only",
        "network": False,
        "credentials": False,
        "mutation": False,
        "shell": False,
    },
    "capabilities": {
        "workspace_read": {
            "classification": "evidence",
            "allowed_modes": ["offline"],
            "mutation": False,
            "requires_approval": False,
        },
        "authority_tool": {
            "classification": "authority",
            "allowed_modes": ["offline"],
            "mutation": False,
            "requires_approval": False,
        },
    },
    "workspace_policy": {"allow_outside_workspace": False},
}


ATTESTATION = {
    "trust_boundary": "local-only",
    "network": False,
    "credentials": False,
    "mutation": False,
    "shell": False,
}


def test_gateone_denies_external_access_in_ghost_mode() -> None:
    decision = GateOnePolicyAdapter(POLICY).decide(
        provider="openai", mode="ghost", memory_allowed=False, external_requested=True
    )
    assert decision.decision == "DENY"


def test_gateone_escalates_cloud_request_without_approval() -> None:
    decision = GateOnePolicyAdapter(POLICY).decide(
        provider="openai", mode="hybrid", memory_allowed=False, external_requested=True
    )
    assert decision.decision == "ESCALATE"


def test_mcp_allows_attested_local_read_and_emits_scar() -> None:
    engine = PolicyEngine(POLICY)
    decision = engine.decide(
        request_id="r1", tool="workspace_read", mode="offline",
        workspace="/workspace", attestation=ATTESTATION
    )
    assert decision.decision == "ALLOW"
    assert len(engine.scar.events) == 1


def test_mcp_accepts_legacy_camel_case_attestation() -> None:
    attestation = {
        "trustBoundary": "local-only",
        "network": False,
        "credentials": False,
        "mutation": False,
        "shell": False,
    }
    decision = PolicyEngine(POLICY).decide(
        request_id="r1-camel", tool="workspace_read", mode="offline",
        workspace="/workspace", attestation=attestation
    )
    assert decision.decision == "ALLOW"


def test_mcp_denies_authority_capability() -> None:
    decision = PolicyEngine(POLICY).decide(
        request_id="r2", tool="authority_tool", mode="offline",
        workspace="/workspace", attestation=ATTESTATION
    )
    assert decision.decision == "DENY"
    assert decision.reason == "authority capability prohibited"


def test_policy_decision_rejects_invalid_state() -> None:
    try:
        PolicyDecision(
            "r3", "tool", "UNKNOWN", "1.0.0", "offline", "local-only",
            False, "bad", "now"
        )
    except ValueError:
        return
    raise AssertionError("invalid policy decision was accepted")


def test_adapter_does_not_invoke_bridge_when_denied() -> None:
    called = False

    def handler() -> None:
        nonlocal called
        called = True

    adapter = MCPPolicyAdapter(PolicyEngine(POLICY), {"authority_tool": handler})
    decision, result = adapter.execute(
        request_id="r4", tool="authority_tool", mode="offline",
        workspace="/workspace", attestation=ATTESTATION
    )
    assert decision.decision == "DENY"
    assert result is None
    assert called is False
