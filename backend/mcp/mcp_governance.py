"""Fail-closed request governance for the local MCP boundary.

This module is deliberately small: it validates request context and capability
admission, records sanitized decisions, and never executes workspace operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class OperationRequest:
    request_id: str
    identity_id: str
    capability_id: str
    operation: str
    mode: str
    workspace: str


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    request_id: str
    identity_id: str
    capability_id: str
    operation: str
    mode: str
    policy_version: str
    decision: str
    reason: str
    timestamp: str


class AuditRecorder:
    """In-memory evidence sink; callers may persist sanitized events separately."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    @property
    def events(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(dict(event) for event in self._events)

    def record(self, decision: AuthorizationDecision) -> None:
        self._events.append(
            {
                "event": "MCP_AUTHORIZATION_DECISION",
                "request_id": decision.request_id,
                "identity_id": decision.identity_id,
                "capability_id": decision.capability_id,
                "operation": decision.operation,
                "mode": decision.mode,
                "policy_version": decision.policy_version,
                "decision": decision.decision,
                "reason": decision.reason,
                "timestamp": decision.timestamp,
            }
        )
        if len(self._events) > 1000:
            del self._events[: len(self._events) - 1000]


class MCPAuthorityAdapter:
    """Authorize MCP operations before the bounded workspace executor runs."""

    def __init__(self, policy: Mapping[str, Any], audit: AuditRecorder | None = None) -> None:
        self.policy = policy
        self.audit = audit or AuditRecorder()

    def authorize(self, request: OperationRequest) -> AuthorizationDecision:
        timestamp = datetime.now(timezone.utc).isoformat()
        version = str(self.policy.get("version", "unknown"))
        capabilities = self.policy.get("capabilities", {})
        capability = capabilities.get(request.capability_id)

        if not request.request_id.strip() or not request.identity_id.strip():
            return self._finish(request, version, "DENY", "missing request identity context", timestamp)
        if not isinstance(capability, Mapping):
            return self._finish(request, version, "DENY", "unknown capability", timestamp)
        if request.mode not in set(capability.get("allowed_modes", ())):
            return self._finish(request, version, "DENY", "mode not permitted", timestamp)
        if bool(capability.get("mutation")):
            return self._finish(request, version, "DENY", "mutation disabled by MCP policy", timestamp)
        if bool(capability.get("requires_approval")):
            return self._finish(request, version, "DENY", "explicit owner approval required", timestamp)
        if capability.get("classification") == "authority":
            return self._finish(request, version, "DENY", "MCP cannot grant authority", timestamp)
        return self._finish(request, version, "ALLOW", "capability permitted", timestamp)

    def _finish(
        self,
        request: OperationRequest,
        policy_version: str,
        decision: str,
        reason: str,
        timestamp: str,
    ) -> AuthorizationDecision:
        result = AuthorizationDecision(
            request.request_id,
            request.identity_id,
            request.capability_id,
            request.operation,
            request.mode,
            policy_version,
            decision,
            reason,
            timestamp,
        )
        self.audit.record(result)
        return result
