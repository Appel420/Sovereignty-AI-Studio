"""Canonical human/machine communication events for the local coordination spine.

Communication is observational. It never grants authority, changes policy, or
creates an execution route. All renderers (text, voice, machine) consume the
same immutable event so the human-visible representations cannot diverge from
the authoritative execution record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import hashlib
import json


CHANNELS = frozenset({"text", "voice", "machine"})
STATUSES = frozenset({"INFO", "PENDING", "APPROVED", "DENIED", "ESCALATED", "COMPLETED", "FAILED"})


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class CommunicationEvent:
    """One canonical event rendered identically across supported channels."""

    event_id: str
    task_id: str
    who: str
    what: str
    when: str
    where: str
    why: str
    how: str
    status: str
    authority: str
    authorization: str
    execution: str
    result: str
    evidence: tuple[str, ...] = ()
    next_action: str | None = None
    channels: tuple[str, ...] = ("text", "voice", "machine")
    timestamp: str = field(default_factory=_timestamp)

    def __post_init__(self) -> None:
        if not self.event_id or not self.task_id:
            raise ValueError("event_id and task_id are required")
        if self.status not in STATUSES:
            raise ValueError(f"unsupported communication status: {self.status}")
        if not self.authority or not self.authorization:
            raise ValueError("authority and authorization are required")
        if not self.execution or not self.result:
            raise ValueError("execution and result are required")
        if not self.channels or any(channel not in CHANNELS for channel in self.channels):
            raise ValueError("channels must contain only text, voice, or machine")
        if len(set(self.channels)) != len(self.channels):
            raise ValueError("communication channels must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "who": self.who,
            "what": self.what,
            "when": self.when,
            "where": self.where,
            "why": self.why,
            "how": self.how,
            "status": self.status,
            "authority": self.authority,
            "authorization": self.authorization,
            "execution": self.execution,
            "result": self.result,
            "evidence": list(self.evidence),
            "next_action": self.next_action,
            "channels": list(self.channels),
            "timestamp": self.timestamp,
        }

    @property
    def event_hash(self) -> str:
        return "sha256:" + hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def machine_payload(self) -> dict[str, Any]:
        """Return the exact canonical event plus its integrity hash."""
        payload = self.to_dict()
        payload["event_hash"] = self.event_hash
        return payload

    def human_text(self) -> str:
        """Produce the concise human-readable representation of this event."""
        return (
            f"{self.status}: {self.what}. "
            f"Who: {self.who}. Where: {self.where}. Why: {self.why}. "
            f"How: {self.how}. Authorization: {self.authorization}. "
            f"Execution: {self.execution}. Result: {self.result}."
        )

    def voice_text(self) -> str:
        """Voice renderer deliberately derives from the same event fields."""
        return self.human_text()
