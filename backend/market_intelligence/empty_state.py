"""Renderer-safe inline empty-state contract."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmptyState:
    title: str
    message: str
    actions: tuple[str, ...]
    blocking: bool = False
    cached_count: int = 0
    last_sync: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "message": self.message,
            "actions": list(self.actions),
            "blocking": self.blocking,
            "cached_count": self.cached_count,
            "last_sync": self.last_sync,
        }


def build_empty_state(
    *,
    record_count: int,
    feed_enabled: bool,
    last_sync: str | None = None,
) -> EmptyState | None:
    """Return an inline state; never a fullscreen lockout."""
    if record_count:
        return None
    if feed_enabled:
        return EmptyState(
            title="0 models loaded",
            message="Waiting for the approved public model feed.",
            actions=("Import Local", "Refresh"),
            cached_count=0,
            last_sync=last_sync,
        )
    return EmptyState(
        title="No feed connected",
        message="The dashboard remains available in local mode.",
        actions=("Import Local", "Connect Feed"),
        cached_count=0,
        last_sync=last_sync,
    )
