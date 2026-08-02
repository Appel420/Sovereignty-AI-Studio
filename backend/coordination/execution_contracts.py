"""Typed contracts for the Genesis -> DevAssist -> evidence boundary.

These objects carry routing metadata only. They do not grant authority, execute
commands, or contain credentials/private payloads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping


MODES = frozenset({"offline", "hybrid", "online"})
DECISIONS = frozenset({"ALLOW", "DENY", "ESCALATE"})


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _hash(value: Mapping[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Genesis routing result; policy remains the authority source."""

    task_id: str
    decision: str
    route: str
    mode: str
    reason_code: str
    policy_hash: str
    requires_owner_approval: bool = False
    evidence_required: bool = True
    timestamp: str = field(default_factory=_timestamp)

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id is required")
        if self.decision not in DECISIONS:
            raise ValueError(f"unsupported decision: {self.decision}")
        if self.mode not in MODES:
            raise ValueError(f"unsupported mode: {self.mode}")
        if not self.route:
            raise ValueError("route is required")
        if not self.policy_hash:
            raise ValueError("policy_hash is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "decision": self.decision,
            "route": self.route,
            "mode": self.mode,
            "reason_code": self.reason_code,
            "policy_hash": self.policy_hash,
            "requires_owner_approval": self.requires_owner_approval,
            "evidence_required": self.evidence_required,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Non-secret result metadata emitted after an authorized execution."""

    task_id: str
    route: str
    mode: str
    status: str
    decision_hash: str
    output_hash: str | None = None
    files_changed: tuple[str, ...] = ()
    network_accessed: bool = False
    timestamp: str = field(default_factory=_timestamp)

    def __post_init__(self) -> None:
        if not self.task_id or not self.route or not self.decision_hash:
            raise ValueError("task_id, route, and decision_hash are required")
        if self.mode not in MODES:
            raise ValueError(f"unsupported mode: {self.mode}")
        if not self.status:
            raise ValueError("status is required")
        if self.mode == "offline" and self.network_accessed:
            raise ValueError("offline execution cannot report network access")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "route": self.route,
            "mode": self.mode,
            "status": self.status,
            "decision_hash": self.decision_hash,
            "output_hash": self.output_hash,
            "files_changed": list(self.files_changed),
            "network_accessed": self.network_accessed,
            "timestamp": self.timestamp,
        }

    @property
    def receipt_hash(self) -> str:
        return _hash(self.to_dict())


@dataclass(frozen=True, slots=True)
class HumanEscalationEvent:
    """Explicit owner-review request for denied or approval-gated work."""

    task_id: str
    reason_code: str
    requested_scope: tuple[str, ...] = ()
    policy_hash: str = ""
    status: str = "PENDING"
    timestamp: str = field(default_factory=_timestamp)

    def __post_init__(self) -> None:
        if not self.task_id or not self.reason_code:
            raise ValueError("task_id and reason_code are required")
        if self.status not in {"PENDING", "APPROVED", "DENIED", "CANCELLED"}:
            raise ValueError(f"unsupported escalation status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "reason_code": self.reason_code,
            "requested_scope": list(self.requested_scope),
            "policy_hash": self.policy_hash,
            "status": self.status,
            "timestamp": self.timestamp,
        }


def make_scar_event(
    *,
    task_id: str,
    event: str,
    route: str,
    mode: str,
    decision: str,
    policy_hash: str,
    receipt_hash: str | None = None,
) -> dict[str, Any]:
    """Build public-safe SCAR/REPMHL binding metadata."""
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")
    if decision not in DECISIONS:
        raise ValueError(f"unsupported decision: {decision}")
    event_payload = {
        "task_id": task_id,
        "event": event,
        "route": route,
        "mode": mode,
        "decision": decision,
        "policy_hash": policy_hash,
        "receipt_hash": receipt_hash,
        "timestamp": _timestamp(),
    }
    event_payload["event_hash"] = _hash(event_payload)
    return event_payload
