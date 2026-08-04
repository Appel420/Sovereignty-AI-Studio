"""Genesis route adapter.

Genesis selects a route after an authority decision. It never grants authority
and never executes a tool.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .execution_contracts import RouteDecision
from .task_envelope import TaskEnvelope


_APPROVED_DECISIONS = frozenset(
    {"ALLOW", "APPROVED", "OWNER_AUTHORIZED", "DELEGATED_AUTHORIZED", "OWNER_OVERRIDE"}
)


def _field(value: object, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


@dataclass(frozen=True, slots=True)
class GenesisRouterAdapter:
    """Choose an execution route from an already-authorized task."""

    routes_by_mode: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        routes = self.routes_by_mode or {
            "offline": "devassist",
            "hybrid": "devassist",
            "online": "sovereignty-runtime",
        }
        object.__setattr__(self, "routes_by_mode", dict(routes))

    def decide(self, task: TaskEnvelope, authorization: object) -> RouteDecision:
        """Return a route only when the supplied authority decision approves."""
        decision = str(_field(authorization, "decision", "")).upper()
        if decision not in _APPROVED_DECISIONS:
            raise PermissionError("route selection requires an approved authority decision")

        policy_hash = _field(authorization, "policy_hash", "")
        if not isinstance(policy_hash, str) or not policy_hash:
            raise PermissionError("approved authority decision must include policy_hash")

        route = self.routes_by_mode.get(task.mode) if self.routes_by_mode else None
        if not route:
            raise ValueError(f"no execution route configured for mode: {task.mode}")

        return RouteDecision(
            task_id=task.task_id,
            decision="ALLOW",
            route=route,
            mode=task.mode,
            reason_code="ROUTE_AUTHORIZED",
            policy_hash=policy_hash,
            requires_owner_approval=bool(
                _field(authorization, "requires_owner_approval", False)
            ),
        )
