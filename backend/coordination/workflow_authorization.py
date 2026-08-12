"""Local device-bound workflow authorization.

This module is an authorization boundary only. It does not execute work, contact
providers, perform profile lookups, store biometrics, or fall back to cloud.
The device/OS supplies a short-lived owner-session assertion; raw fingerprints,
IMEIs, keys, and private payloads never enter this module.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import secrets
from typing import Any

ALLOW = "ALLOW"
DENY = "DENY"
UNKNOWN = "UNKNOWN"


class DecisionCode(str, Enum):
    ALLOWED = "AUTH-000"
    OWNER_SESSION_REQUIRED = "AUTH-001"
    OWNER_SESSION_MISMATCH = "AUTH-002"
    DEVICE_NOT_REGISTERED = "AUTH-003"
    INVALID_SIGNATURE = "FAIL-001"
    SIGNATURE_UNAVAILABLE = "FAIL-002"
    POLICY_DENIED = "POLICY-001"
    REPLAYED_REQUEST = "REPLAY-001"
    EXPIRED_REQUEST = "EXPIRE-001"
    UNKNOWN_DESTINATION = "EXEC-001"
    STATE_PERMISSION_DENIED = "STATE-002"
    RETENTION_NOT_DECLARED = "RET-001"
    AUDIT_UNAVAILABLE = "AUDIT-001"
    LOCAL_UI_LOCKED = "UI-001"


class ScreenState(str, Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Mapping[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class AuthenticatedOwner:
    login: str
    device_id: str
    session_id: str
    fingerprint_verified: bool
    authenticated_at: str

    def __post_init__(self) -> None:
        if not self.login or not self.device_id or not self.session_id:
            raise ValueError("owner login, device_id, and session_id are required")
        if not self.fingerprint_verified:
            raise ValueError("local owner verification is required")
        _parse_time(self.authenticated_at)


@dataclass(frozen=True, slots=True)
class WorkflowEnvelope:
    version: str
    workflow_id: str
    issuer: str
    device_id: str
    action: str
    target: str
    scope: tuple[str, ...] = ()
    branch: str | None = None
    artifact_hashes: tuple[str, ...] = ()
    created_at: str = ""
    expires_at: str = ""
    nonce: str = ""
    sequence_number: int = 0
    signature: str = ""

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "workflow_id": self.workflow_id,
            "issuer": self.issuer,
            "device_id": self.device_id,
            "action": self.action,
            "target": self.target,
            "scope": list(self.scope),
            "branch": self.branch,
            "artifact_hashes": list(self.artifact_hashes),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "sequence_number": self.sequence_number,
        }

    @property
    def payload_hash(self) -> str:
        return _hash(self.unsigned_payload())

    def validate(self, now: datetime) -> None:
        required = (self.version, self.workflow_id, self.issuer, self.device_id,
                    self.action, self.target, self.created_at, self.expires_at,
                    self.nonce, self.signature)
        if any(not isinstance(value, str) or not value.strip() for value in required):
            raise ValueError("workflow envelope has missing required fields")
        if self.sequence_number < 0:
            raise ValueError("sequence_number must be non-negative")
        created = _parse_time(self.created_at)
        expires = _parse_time(self.expires_at)
        if expires <= created or expires <= now.astimezone(timezone.utc):
            raise ValueError("workflow envelope is expired or has invalid bounds")


@dataclass(frozen=True, slots=True)
class CloudExecutionCapability:
    capability_id: str
    workflow_id: str
    destination: str
    action: str
    scope: tuple[str, ...]
    data_classification: str
    policy_hash: str
    approval_event_id: str
    issued_at: str
    expires_at: str
    signature: str


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    decision: str
    code: DecisionCode
    reason: str
    workflow_id: str
    policy_hash: str
    capability: CloudExecutionCapability | None = None
    screen_state: ScreenState = ScreenState.ACTIVE
    evidence: Mapping[str, Any] = field(default_factory=dict)


class ReplayStore:
    def __init__(self) -> None:
        self._seen: set[tuple[str, str, int]] = set()

    def contains(self, device_id: str, nonce: str, sequence_number: int) -> bool:
        return (device_id, nonce, sequence_number) in self._seen

    def record(self, device_id: str, nonce: str, sequence_number: int) -> None:
        self._seen.add((device_id, nonce, sequence_number))


class WorkflowAuthorizationService:
    """Authorize a workflow; callers must execute only after ALLOW."""

    def __init__(
        self,
        *,
        device_registered: Callable[[str], bool],
        verify_signature: Callable[[WorkflowEnvelope], bool | None],
        policy_allows: Callable[[WorkflowEnvelope], bool],
        audit_append: Callable[[Mapping[str, Any]], Any],
        owner_login: str = "Appel420",
        verify_owner_session: Callable[[AuthenticatedOwner], bool | None] | None = None,
        replay_store: ReplayStore | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._device_registered = device_registered
        self._verify_signature = verify_signature
        self._policy_allows = policy_allows
        self._audit_append = audit_append
        self._owner_login = owner_login
        self._verify_owner_session = verify_owner_session or (lambda owner: owner.fingerprint_verified)
        self._replay = replay_store or ReplayStore()
        self._now = now or (lambda: datetime.now(timezone.utc))

    def authorize(
        self,
        envelope: WorkflowEnvelope,
        *,
        owner: AuthenticatedOwner | None = None,
        execution_target: str = "local",
        state_permission: str = "none",
        retention_permission: str = "none",
        owner_confirmation: bool = False,
        data_classification: str = "local",
    ) -> AuthorizationResult:
        policy_hash = _hash({"workflow": envelope.workflow_id, "action": envelope.action})
        base = {
            "event": "WORKFLOW_AUTHORIZATION",
            "workflow_id": envelope.workflow_id,
            "device_id": envelope.device_id,
            "owner_login": owner.login if owner else None,
            "target": envelope.target,
            "action": envelope.action,
            "execution_target": execution_target,
            "policy_hash": policy_hash,
        }
        if owner is None or owner.login != self._owner_login or owner.device_id != envelope.device_id:
            return self._deny(base, DecisionCode.OWNER_SESSION_MISMATCH, "recognized owner session is required", policy_hash, lock=True)
        try:
            if self._verify_owner_session(owner) is not True:
                return self._deny(base, DecisionCode.OWNER_SESSION_REQUIRED, "local owner assertion was not verified", policy_hash, lock=True)
            envelope.validate(self._now())
        except (TypeError, ValueError) as exc:
            return self._deny(base, DecisionCode.EXPIRED_REQUEST, str(exc), policy_hash)
        if not self._device_registered(envelope.device_id):
            return self._deny(base, DecisionCode.DEVICE_NOT_REGISTERED, "device is not registered", policy_hash, lock=True)
        signature = self._verify_signature(envelope)
        if signature is not True:
            code = DecisionCode.INVALID_SIGNATURE if signature is False else DecisionCode.SIGNATURE_UNAVAILABLE
            return self._deny(base, code, "signature verification did not pass", policy_hash, unknown=signature is None)
        if self._replay.contains(envelope.device_id, envelope.nonce, envelope.sequence_number):
            return self._deny(base, DecisionCode.REPLAYED_REQUEST, "nonce or sequence was already used", policy_hash)
        if execution_target not in {"local", "external"}:
            return self._deny(base, DecisionCode.UNKNOWN_DESTINATION, "unknown execution target", policy_hash)
        if not self._policy_allows(envelope):
            return self._deny(base, DecisionCode.POLICY_DENIED, "policy did not authorize workflow", policy_hash)
        if execution_target == "external":
            if not owner_confirmation:
                return self._deny(base, DecisionCode.OWNER_SESSION_REQUIRED, "external execution requires owner confirmation", policy_hash)
            if state_permission not in {"explicit_files", "approved_context"}:
                return self._deny(base, DecisionCode.STATE_PERMISSION_DENIED, "external state permission is missing", policy_hash)
            if retention_permission != "declared":
                return self._deny(base, DecisionCode.RETENTION_NOT_DECLARED, "external retention must be declared", policy_hash)
        self._replay.record(envelope.device_id, envelope.nonce, envelope.sequence_number)
        capability = None
        if execution_target == "external":
            issued = self._now().astimezone(timezone.utc).isoformat()
            capability = CloudExecutionCapability(
                capability_id=secrets.token_urlsafe(18), workflow_id=envelope.workflow_id,
                destination=envelope.target, action=envelope.action, scope=envelope.scope,
                data_classification=data_classification, policy_hash=policy_hash,
                approval_event_id=f"approval:{envelope.workflow_id}", issued_at=issued,
                expires_at=envelope.expires_at, signature=envelope.signature,
            )
        evidence = {**base, "decision": ALLOW, "code": DecisionCode.ALLOWED.value,
                    "owner_session_verified": True, "signature_verified": True,
                    "state_permission": state_permission, "retention_permission": retention_permission,
                    "capability_issued": capability is not None, "data_sent": False}
        if capability:
            evidence["capability_id"] = capability.capability_id
        self._append_or_fail(evidence)
        return AuthorizationResult(ALLOW, DecisionCode.ALLOWED, "authorized", envelope.workflow_id, policy_hash, capability, evidence=evidence)

    def _deny(self, base: Mapping[str, Any], code: DecisionCode, reason: str, policy_hash: str, *, lock: bool = False, unknown: bool = False) -> AuthorizationResult:
        decision = UNKNOWN if unknown else DENY
        evidence = {**base, "decision": decision, "code": code.value, "reason": reason, "data_sent": False}
        try:
            self._audit_append(evidence)
        except Exception as exc:
            return AuthorizationResult(UNKNOWN, DecisionCode.AUDIT_UNAVAILABLE, "audit unavailable", base["workflow_id"], policy_hash, screen_state=ScreenState.LOCKED if lock else ScreenState.ACTIVE, evidence={**evidence, "audit_error": str(exc)})
        return AuthorizationResult(decision, code, reason, base["workflow_id"], policy_hash, screen_state=ScreenState.LOCKED if lock else ScreenState.ACTIVE, evidence=evidence)

    def _append_or_fail(self, evidence: Mapping[str, Any]) -> None:
        try:
            self._audit_append(evidence)
        except Exception as exc:
            raise PermissionError("AUDIT-001/audit unavailable") from exc


__all__ = ["ALLOW", "DENY", "UNKNOWN", "AuthenticatedOwner", "AuthorizationResult", "CloudExecutionCapability", "DecisionCode", "ReplayStore", "ScreenState", "WorkflowAuthorizationService", "WorkflowEnvelope"]
