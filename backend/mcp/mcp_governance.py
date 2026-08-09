"""Fail-closed authorization boundary for the local MCP surface.

This module is deliberately independent of workspace execution.  MCP is
never allowed to manufacture an identity, capability grant, or authority.
The trusted local host must inject an authenticated session context.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class IdentityContext:
    """Authenticated identity supplied by a trusted local authority."""

    identity_id: str
    authenticated: bool
    attestation: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    """Capability granted by the authority plane, not by MCP."""

    capability_id: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class OperationRequest:
    request_id: str
    identity: IdentityContext
    capability: CapabilityRecord
    operation: str
    mode: str
    workspace: str

    @property
    def identity_id(self) -> str:
        return self.identity.identity_id

    @property
    def capability_id(self) -> str:
        return self.capability.capability_id


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
    """Sanitized evidence sink; it never receives credentials or payloads."""

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

    def record_execution(self, *, request: OperationRequest, result: str) -> None:
        self._events.append(
            {
                "event": "MCP_EXECUTION_RESULT",
                "request_id": request.request_id,
                "identity_id": request.identity_id,
                "capability_id": request.capability_id,
                "operation": request.operation,
                "mode": request.mode,
                "result": result,
            }
        )


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

        if not request.request_id.strip():
            return self._finish(request, version, "DENY", "missing request id", timestamp)
        if not request.identity.authenticated or not request.identity.identity_id.strip():
            return self._finish(request, version, "DENY", "unauthenticated identity", timestamp)
        if not request.capability.active:
            return self._finish(request, version, "DENY", "inactive capability grant", timestamp)
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
        if not self._valid_attestation(request.identity.attestation):
            return self._finish(request, version, "DENY", "invalid local attestation", timestamp)
        return self._finish(request, version, "ALLOW", "capability permitted", timestamp)

    def _valid_attestation(self, attestation: Mapping[str, Any]) -> bool:
        requirements = self.policy.get("bridge_requirements", {})
        if not isinstance(requirements, Mapping) or not attestation:
            return False
        return all(attestation.get(key) == value for key, value in requirements.items())

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
        try:
            self.audit.record(result)
        except Exception as error:
            # Evidence failure is a hard authorization failure.  Do not allow
            # execution to proceed when the required audit boundary is broken.
            return AuthorizationDecision(
                result.request_id,
                result.identity_id,
                result.capability_id,
                result.operation,
                result.mode,
                result.policy_version,
                "DENY",
                f"audit failure: {type(error).__name__}",
                result.timestamp,
            )
        return result
