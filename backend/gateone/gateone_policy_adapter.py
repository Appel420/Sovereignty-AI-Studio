"""GateOne provider/state policy adapter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class GateOneDecision:
    decision: str
    provider: str
    mode: str
    memory_allowed: bool
    external_access: bool
    reason: str
    policy_version: str


class GateOnePolicyAdapter:
    """Evaluate provider, memory, and cloud policy before routing."""

    def __init__(self, policy: Mapping[str, Any]) -> None:
        self.policy = policy

    def decide(
        self,
        *,
        provider: str,
        mode: str,
        memory_allowed: bool,
        external_requested: bool,
        explicit_cloud_approval: bool = False,
    ) -> GateOneDecision:
        version = str(self.policy.get("version", "unknown"))
        provider_policy = self.policy.get("provider_policy", {})
        allowed = set(provider_policy.get("allow", ()))
        denied = set(provider_policy.get("deny", ()))
        if provider in denied or provider not in allowed:
            return GateOneDecision("DENY", provider, mode, False, False, "provider denied by GateOne policy", version)
        if mode in {"ghost", "offline"} and external_requested:
            return GateOneDecision("DENY", provider, mode, False, False, "external access forbidden in local mode", version)
        if external_requested and not explicit_cloud_approval:
            return GateOneDecision("ESCALATE", provider, mode, False, False, "explicit cloud approval required", version)
        return GateOneDecision("ALLOW", provider, mode, bool(memory_allowed), bool(external_requested), "provider permitted by policy", version)
