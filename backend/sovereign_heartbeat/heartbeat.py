"""Sovereign, append-only heartbeat/checkpoint state.

The heartbeat is deliberately local-first: it records health and state transitions
without requiring a network service or third-party runtime dependency.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HeartbeatState:
    sequence: int = 0
    status: str = "INITIALIZING"
    last_beat: str | None = None
    last_checkpoint: str | None = None
    repository_head: str | None = None
    lane: str = "GPT/Codex"
    base: str = "Collaboration"
    memory_store: str = "local"
    evidence_sequence: int = 0
    anomalies: list[str] = field(default_factory=list)


class SovereignHeartbeat:
    """Persist heartbeat state as an append-only JSONL journal plus a snapshot."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.journal = self.root / "heartbeat.jsonl"
        self.snapshot = self.root / "heartbeat.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _atomic_write(path: Path, payload: str) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def load(self) -> HeartbeatState:
        if not self.snapshot.exists():
            return HeartbeatState()
        return HeartbeatState(**json.loads(self.snapshot.read_text(encoding="utf-8")))

    def beat(self, *, status: str, repository_head: str | None = None,
             anomalies: list[str] | None = None) -> HeartbeatState:
        state = self.load()
        now = self._now()
        state.sequence += 1
        state.status = status
        state.last_beat = now
        state.repository_head = repository_head or state.repository_head
        state.anomalies = list(anomalies or [])
        self._append({"type": "heartbeat", "at": now, **asdict(state)})
        self._write_snapshot(state)
        return state

    def checkpoint(self, *, reason: str,
                   repository_head: str | None = None) -> HeartbeatState:
        state = self.load()
        now = self._now()
        state.sequence += 1
        state.evidence_sequence += 1
        state.last_checkpoint = now
        state.last_beat = now
        state.repository_head = repository_head or state.repository_head
        self._append({"type": "checkpoint", "reason": reason, "at": now, **asdict(state)})
        self._write_snapshot(state)
        return state

    def _append(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(line.encode("utf-8")).hexdigest()
        record = json.dumps({"event": event, "sha256": digest}, sort_keys=True)
        with self.journal.open("a", encoding="utf-8") as handle:
            handle.write(record + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _write_snapshot(self, state: HeartbeatState) -> None:
        self._atomic_write(self.snapshot, json.dumps(asdict(state), indent=2, sort_keys=True) + "\n")
