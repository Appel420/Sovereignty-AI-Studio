"""Fail-closed GateOne/MCP policy evaluation for local capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DECISION_STATES = frozenset({"ALLOW", "DENY", "ESCALATE"})


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    request_id: str
    tool: str
    decision: str
    policy_version: str
    mode: str
    trust_boundary: str
    mutation: bool
    reason: str
    timestamp: str

    def __post_init__(self) -> None:
        if self.decision not in DECISION_STATES:
            raise ValueError(f"Invalid policy decision: {self.decision}")


class CapabilityRegistry:
    REQUIRED_FIELDS = frozenset({"classification", "allowed_modes", "mutation", "requires_approval"})

    def __init__(self, policy: Mapping[str, Any]) -> None:
        self._capabilities = policy.get("capabilities", {})

    def get(self, tool: str) -> Mapping[str, Any] | None:
        capability = self._capabilities.get(tool)
        if not isinstance(capability, Mapping):
            return None
        if not self.REQUIRED_FIELDS.issubset(capability):
            return None
        return capability


class SCAREmitter:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    @property
    def events(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(dict(event) for event in self._events)

    def emit(self, decision: PolicyDecision, workspace: str) -> None:
        self._events.append({
            "event": "CAPABILITY_DECISION",
            "request_id": decision.request_id,
            "tool": decision.tool,
            "workspace": workspace,
            "mode": decision.mode,
            "decision": decision.decision,
            "mutation": decision.mutation,
            "trust_boundary": decision.trust_boundary,
            "policy_version": decision.policy_version,
            "timestamp": decision.timestamp,
            "reason": decision.reason,
        })


class PolicyEngine:
    """Evaluate capability admission; never execute capabilities."""

    def __init__(self, policy: Mapping[str, Any], scar: SCAREmitter | None = None) -> None:
        self.policy = policy
        self.registry = CapabilityRegistry(policy)
        self.scar = scar or SCAREmitter()

    @staticmethod
    def load(path: str | Path = "mcp_policy.json") -> "PolicyEngine":
        import json

        with Path(path).open(encoding="utf-8") as handle:
            return PolicyEngine(json.load(handle))

    def decide(
        self,
        *,
        request_id: str,
        tool: str,
        mode: str = "offline",
        workspace: str = ".",
        attestation: Mapping[str, Any] | None = None,
        arguments: Mapping[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> PolicyDecision:
        del arguments
        now = timestamp or datetime.now(timezone.utc).isoformat()
        version = str(self.policy.get("version", "unknown"))
        trust_boundary = str(self.policy.get("bridge_requirements", {}).get("trust_boundary", "unknown"))
        capability = self.registry.get(tool)

        if capability is None:
            return self._finish(PolicyDecision(request_id, tool, "DENY", version, mode, trust_boundary, False, "unknown or malformed capability", now), workspace)
        if capability.get("classification") == "authority":
            return self._finish(PolicyDecision(request_id, tool, "DENY", version, mode, trust_boundary, bool(capability.get("mutation")), "authority capability prohibited", now), workspace)
        if mode not in set(capability.get("allowed_modes", ())):
            return self._finish(PolicyDecision(request_id, tool, "DENY", version, mode, trust_boundary, bool(capability.get("mutation")), "mode not permitted", now), workspace)
        if bool(capability.get("mutation")):
            return self._finish(PolicyDecision(request_id, tool, "DENY", version, mode, trust_boundary, True, "mutation is disabled by local policy", now), workspace)
        if bool(capability.get("requires_approval")):
            return self._finish(PolicyDecision(request_id, tool, "ESCALATE", version, mode, trust_boundary, False, "explicit owner approval required", now), workspace)
        if not self._valid_attestation(attestation):
            return self._finish(PolicyDecision(request_id, tool, "DENY", version, mode, trust_boundary, False, "invalid or missing local attestation", now), workspace)
        if not self._valid_workspace(workspace):
            return self._finish(PolicyDecision(request_id, tool, "DENY", version, mode, trust_boundary, False, "workspace outside approved boundary", now), workspace)
        return self._finish(PolicyDecision(request_id, tool, "ALLOW", version, mode, trust_boundary, False, "read-only local capability permitted", now), workspace)

    def _finish(self, decision: PolicyDecision, workspace: str) -> PolicyDecision:
        self.scar.emit(decision, workspace)
        return decision

    def _valid_attestation(self, attestation: Mapping[str, Any] | None) -> bool:
        required = self.policy.get("bridge_requirements", {})
        if not attestation:
            return False
        return all(attestation.get(key) == value for key, value in required.items())

    def _valid_workspace(self, workspace: str) -> bool:
        path = Path(workspace)
        if self.policy.get("workspace_policy", {}).get("allow_outside_workspace") is False:
            return not path.is_absolute() or str(path).startswith("/workspace")
        return True
