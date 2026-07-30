"""Adapter that enforces policy before invoking a bounded local bridge."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .policy_engine import PolicyDecision, PolicyEngine


class MCPPolicyAdapter:
    def __init__(self, engine: PolicyEngine, bridge: Mapping[str, Callable[..., Any]]) -> None:
        self.engine = engine
        self.bridge = dict(bridge)

    def execute(
        self,
        *,
        request_id: str,
        tool: str,
        mode: str = "offline",
        workspace: str = ".",
        attestation: Mapping[str, Any] | None = None,
        arguments: Mapping[str, Any] | None = None,
    ) -> tuple[PolicyDecision, Any | None]:
        decision = self.engine.decide(
            request_id=request_id,
            tool=tool,
            mode=mode,
            workspace=workspace,
            attestation=attestation,
            arguments=arguments,
        )
        if decision.decision != "ALLOW":
            return decision, None
        handler = self.bridge.get(tool)
        if handler is None:
            return decision, None
        return decision, handler(**dict(arguments or {}))
