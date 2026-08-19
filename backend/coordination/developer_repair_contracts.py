"""Developer diagnostics and human authorization contracts.

Diagnostics may discover and explain repairs, but they never grant authority.
A repair becomes executable only after an explicit owner authorization decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RepairState(str, Enum):
    PROPOSED = "PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    DECLINED = "DECLINED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    BLOCKED = "BLOCKED"


class AccessState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DENIED = "DENIED"
    NOT_REQUESTED = "NOT_REQUESTED"


@dataclass(frozen=True, slots=True)
class RepairProposal:
    """A proposed repair with enough information for a human to decide."""

    proposal_id: str
    problem: str
    cause: str
    explanation: str
    fix: str
    scope: tuple[str, ...]
    risk: str
    access: AccessState = AccessState.NOT_REQUESTED
    state: RepairState = RepairState.PROPOSED
    _transition: bool = False

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.problem or not self.cause:
            raise ValueError("proposal_id, problem, and cause are required")
        if not self.fix or not self.scope:
            raise ValueError("fix and scope are required")
        if self.state is not RepairState.PROPOSED and not self._transition:
            raise ValueError("new repair proposals must start in PROPOSED state")

    def authorize(self) -> "RepairProposal":
        if self.access is AccessState.DENIED:
            raise PermissionError("required access is denied")
        return RepairProposal(
            proposal_id=self.proposal_id,
            problem=self.problem,
            cause=self.cause,
            explanation=self.explanation,
            fix=self.fix,
            scope=self.scope,
            risk=self.risk,
            access=self.access,
            state=RepairState.AUTHORIZED,
        )

    def decline(self) -> "RepairProposal":
        return RepairProposal(
            proposal_id=self.proposal_id,
            problem=self.problem,
            cause=self.cause,
            explanation=self.explanation,
            fix=self.fix,
            scope=self.scope,
            risk=self.risk,
            access=self.access,
            state=RepairState.DECLINED,
        )
