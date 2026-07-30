"""Non-destructive conflict detection for parallel agent work."""
from __future__ import annotations

from dataclasses import dataclass

from .task_envelope import TaskEnvelope


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    task_id: str
    conflicts_with: tuple[str, ...]
    scope: tuple[str, ...]
    reason: str
    status: str = "pending-council-review"


class ConflictManager:
    """Detect overlapping scopes without deleting, merging, or overwriting work."""

    def __init__(self) -> None:
        self._active: dict[str, TaskEnvelope] = {}

    @staticmethod
    def _overlap(left: TaskEnvelope, right: TaskEnvelope) -> tuple[str, ...]:
        return tuple(sorted(set(left.scope).intersection(right.scope)))

    def register(self, envelope: TaskEnvelope) -> ConflictRecord | None:
        conflicts = [
            task
            for task in self._active.values()
            if task.task_id != envelope.task_id and self._overlap(task, envelope)
        ]
        if conflicts:
            return ConflictRecord(
                task_id=envelope.task_id,
                conflicts_with=tuple(sorted(task.task_id for task in conflicts)),
                scope=tuple(sorted({item for task in conflicts for item in self._overlap(task, envelope)})),
                reason="overlapping file or capability scope requires council review",
            )
        self._active[envelope.task_id] = envelope
        return None

    def release(self, task_id: str) -> None:
        self._active.pop(task_id, None)

    def active(self) -> tuple[TaskEnvelope, ...]:
        return tuple(self._active.values())
