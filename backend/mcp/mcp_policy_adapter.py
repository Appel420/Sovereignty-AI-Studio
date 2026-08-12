"""Adapter that enforces policy and authenticated session context before execution."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .mcp_governance import IdentityContext
from .policy_engine import PolicyDecision, PolicyEngine


class MCPPolicyAdapter:
    """Compatibility adapter with the same fail-closed identity boundary."""

    def __init__(self, engine: PolicyEngine, bridge: Mapping[str, Callable[..., Any]]) -> None:
        self.engine = engine
        self.bridge = dict(bridge)

    def execute(
        self,
        *,
        request_id: str,
        tool: str,
        identity: IdentityContext | None,
        mode: str = "offline",
        workspace: str = ".",
        arguments: Mapping[str, Any] | None = None,
    ) -> tuple[PolicyDecision, Any | None]:
        if identity is None or not identity.authenticated or not identity.identity_id.strip():
            decision = self.engine.decide(
                request_id=request_id,
                tool=tool,
                mode=mode,
                workspace=workspace,
                attestation={},
                arguments=arguments,
            )
            return decision, None

        decision = self.engine.decide(
            request_id=request_id,
            tool=tool,
            mode=mode,
            workspace=workspace,
            attestation=identity.attestation,
            arguments=arguments,
        )
        if decision.decision != "ALLOW":
            return decision, None
        handler = self.bridge.get(tool)
        if handler is None:
            return decision, None
        return decision, handler(**dict(arguments or {}))
