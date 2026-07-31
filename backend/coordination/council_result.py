"""Owner-visible council outcome; agents advise, the owner decides."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .branch_registry import BranchOwner
from .conflict_manager import ConflictRecord

if TYPE_CHECKING:
    from .lease import LeaseToken


@dataclass(frozen=True, slots=True)
class AgentRoute:
    agent: str
    branch: str
    scope: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CouncilResult:
    approved: bool
    routes: tuple[AgentRoute, ...] = ()
    conflicts: tuple[ConflictRecord, ...] = ()
    notes: tuple[str, ...] = ()
    requires_owner_approval: bool = True
    lease: "LeaseToken | None" = None

    @classmethod
    def denied(cls, note: str) -> "CouncilResult":
        return cls(approved=False, notes=(note,))

    @classmethod
    def route_for(
        cls,
        owner: BranchOwner,
        scope: tuple[str, ...],
        lease: "LeaseToken | None" = None,
    ) -> "CouncilResult":
        return cls(
            approved=True,
            routes=(AgentRoute(owner.owner, owner.branch, scope),),
            notes=("Agents provide analysis; integration remains owner-approved.",),
            lease=lease,
        )
