"""Non-destructive scope holds and conflict detection for parallel agent work.

Holds are in-memory for a single process. Overlapping path prefixes or exact
scope tags block a second primary until the first task is released. Nothing is
deleted, merged, or overwritten here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .task_envelope import TaskEnvelope


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    task_id: str
    conflicts_with: tuple[str, ...]
    scope: tuple[str, ...]
    reason: str
    status: str = "pending-council-review"


@dataclass(frozen=True, slots=True)
class ScopeHold:
    task_id: str
    branch: str | None
    scope: tuple[str, ...]
    held_at: str  # UTC ISO-8601


def _normalize(item: str) -> str:
    text = str(item).strip().replace("\\", "/")
    if text.endswith("/") and len(text) > 1:
        text = text.rstrip("/")
    return text


def scopes_overlap(left: str, right: str) -> bool:
    """Exact match or path-prefix overlap (file scopes).

    Tag scopes like ``security`` only conflict on exact match.
    Path scopes like ``backend/api`` conflict with ``backend/api/router.py``.
    """
    a, b = _normalize(left), _normalize(right)
    if not a or not b:
        return False
    if a == b:
        return True
    # Path-like if either contains a slash or looks like a repo path
    pathish = ("/" in a or "/" in b or a.endswith(".py") or b.endswith(".py"))
    if not pathish:
        return False
    return a.startswith(b + "/") or b.startswith(a + "/")


def envelope_overlap(left: TaskEnvelope, right: TaskEnvelope) -> tuple[str, ...]:
    hits: set[str] = set()
    for a in left.scope:
        for b in right.scope:
            if scopes_overlap(a, b):
                hits.add(_normalize(a))
                hits.add(_normalize(b))
    return tuple(sorted(hits))


class ConflictManager:
    """Register scope holds; detect overlap without mutating repositories."""

    def __init__(self) -> None:
        self._active: dict[str, TaskEnvelope] = {}
        self._holds: dict[str, ScopeHold] = {}

    def check(self, envelope: TaskEnvelope) -> ConflictRecord | None:
        """Return a conflict if envelope would overlap an active hold; do not register."""
        conflicts = [
            task
            for task in self._active.values()
            if task.task_id != envelope.task_id and envelope_overlap(task, envelope)
        ]
        if not conflicts:
            return None
        overlapped: set[str] = set()
        for task in conflicts:
            overlapped.update(envelope_overlap(task, envelope))
        return ConflictRecord(
            task_id=envelope.task_id,
            conflicts_with=tuple(sorted(task.task_id for task in conflicts)),
            scope=tuple(sorted(overlapped)),
            reason="overlapping file or capability scope requires council review",
        )

    def register(self, envelope: TaskEnvelope) -> ConflictRecord | None:
        """Try to take a scope hold. On conflict, do not register the new task."""
        conflict = self.check(envelope)
        if conflict is not None:
            return conflict
        self._active[envelope.task_id] = envelope
        self._holds[envelope.task_id] = ScopeHold(
            task_id=envelope.task_id,
            branch=envelope.branch,
            scope=tuple(_normalize(s) for s in envelope.scope),
            held_at=datetime.now(timezone.utc).isoformat(),
        )
        return None

    def hold(self, envelope: TaskEnvelope) -> ConflictRecord | None:
        """Alias for register — explicit scope-hold vocabulary."""
        return self.register(envelope)

    def release(self, task_id: str) -> None:
        self._active.pop(task_id, None)
        self._holds.pop(task_id, None)

    def active(self) -> tuple[TaskEnvelope, ...]:
        return tuple(self._active.values())

    def holds(self) -> tuple[ScopeHold, ...]:
        return tuple(self._holds.values())
