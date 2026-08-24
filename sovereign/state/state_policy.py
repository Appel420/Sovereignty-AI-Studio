"""Device State Sovereignty Policy enforcement.

Execution, persistence, and retention are independent capabilities. The
policy is evaluated before routing and produces an explicit state report.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class StateMode(StrEnum):
    DEVICE_ONLY = "DEVICE_ONLY"
    DEVICE_FIRST = "DEVICE_FIRST"


class ExternalMemory(StrEnum):
    DISABLED = "DISABLED"
    PER_OPERATION = "PER_OPERATION"
    OPT_IN_ONLY = "OPT_IN_ONLY"


class StatePolicyError(ValueError):
    pass


@dataclass(frozen=True)
class StatePolicy:
    mode: StateMode = StateMode.DEVICE_ONLY
    allow_external_memory: bool = False
    allow_provider_training: bool = False
    allow_cross_session_sync: bool = False
    allow_telemetry: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "StatePolicy":
        value = value or {}
        mode = str(value.get("mode", StateMode.DEVICE_ONLY.value)).upper()
        if mode not in {m.value for m in StateMode}:
            raise StatePolicyError(f"invalid state policy mode: {mode}")
        return cls(
            mode=StateMode(mode),
            allow_external_memory=bool(value.get("allow_external_memory", False)),
            allow_provider_training=bool(value.get("allow_provider_training", False)),
            allow_cross_session_sync=bool(value.get("allow_cross_session_sync", False)),
            allow_telemetry=bool(value.get("allow_telemetry", False)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "allow_external_memory": self.allow_external_memory,
            "allow_provider_training": self.allow_provider_training,
            "allow_cross_session_sync": self.allow_cross_session_sync,
            "allow_telemetry": self.allow_telemetry,
        }


@dataclass(frozen=True)
class StateReport:
    state_used: str
    external_data_sent: bool
    external_state_written: bool
    policy_verified: bool
    blocked: bool = False
    reason: str | None = None
    authorization_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result = {
            "state_used": self.state_used,
            "external_data_sent": self.external_data_sent,
            "external_state_written": self.external_state_written,
            "policy_verified": self.policy_verified,
        }
        if self.blocked:
            result.update({"blocked": True, "reason": self.reason})
        if self.authorization_id:
            result["authorization_id"] = self.authorization_id
        return result


def evaluate_external_route(
    policy: StatePolicy,
    *,
    execution_external: bool,
    external_memory_requested: bool = False,
    cross_session_sync_requested: bool = False,
    owner_authorized: bool = False,
) -> StateReport:
    """Fail closed when the destination cannot satisfy the state boundary."""
    if not execution_external:
        return StateReport("DEVICE_LOCAL", False, False, True)

    if policy.mode == StateMode.DEVICE_ONLY:
        return StateReport(
            "DEVICE_LOCAL", False, False, True, True,
            "STATE_SYNC_BLOCKED: DEVICE_ONLY policy",
        )

    if external_memory_requested:
        if not policy.allow_external_memory or not owner_authorized:
            return StateReport(
                "DEVICE_LOCAL", False, False, True, True,
                "STATE_SYNC_BLOCKED: external persistence not authorized",
            )

    if cross_session_sync_requested:
        if not policy.allow_cross_session_sync or not owner_authorized:
            return StateReport(
                "DEVICE_LOCAL", False, False, True, True,
                "STATE_SYNC_BLOCKED: cross-session synchronization not authorized",
            )

    return StateReport(
        "DEVICE_LOCAL",
        True,
        external_memory_requested or cross_session_sync_requested,
        True,
        False,
        authorization_id="OWNER_APPROVED" if owner_authorized else None,
    )
