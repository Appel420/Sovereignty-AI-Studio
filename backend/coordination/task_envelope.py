"""Immutable task envelope passed through the local coordination spine."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TaskEnvelope:
    task_id: str
    requester: str
    owner: str
    requested_agent: str | None = None
    branch: str | None = None
    scope: tuple[str, ...] = ()
    mode: str = "offline"
    write_policy: str = "branch-only"
    requires_owner_approval: bool = False
    parallel_group: str | None = None
    conflicts_with: tuple[str, ...] = ()
    merge_required: bool = True

    def __post_init__(self) -> None:
        if not self.task_id or not self.requester or not self.owner:
            raise ValueError("task_id, requester, and owner are required")
        if self.write_policy != "branch-only":
            raise ValueError("coordination tasks must use branch-only writes")
        if self.branch == "main":
            raise ValueError("direct writes to main are forbidden")
        if self.mode not in {"offline", "hybrid", "online"}:
            raise ValueError(f"Unsupported coordination mode: {self.mode}")
