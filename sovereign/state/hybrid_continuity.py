"""Device-local Hybrid continuity aggregation.

Per-agent records remain detailed source records. Hybrid is only the verified
cross-agent aggregate used to resume work; it never writes to providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


VALID_STATES = {
    "OBSERVED", "PROPOSED", "AUTHORIZED", "EXECUTING",
    "COMPLETED", "VERIFIED", "BLOCKED", "FAILED",
}


@dataclass(frozen=True)
class HybridRecord:
    record_id: str
    who: Mapping[str, Any]
    what: Mapping[str, Any]
    when: Mapping[str, Any]
    where: Mapping[str, Any]
    why: Mapping[str, Any]
    how: Mapping[str, Any]
    state: str
    proof: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"invalid continuity state: {self.state}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "who": dict(self.who),
            "what": dict(self.what),
            "when": dict(self.when),
            "where": dict(self.where),
            "why": dict(self.why),
            "how": dict(self.how),
            "state": self.state,
            "proof": dict(self.proof),
        }


class HybridContinuityStore:
    """Append-only JSONL store rooted on the device filesystem."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "hybrid-continuity.jsonl"

    def append(self, *, who: Mapping[str, Any], what: Mapping[str, Any],
               where: Mapping[str, Any], why: Mapping[str, Any],
               how: Mapping[str, Any], state: str,
               proof: Mapping[str, Any]) -> HybridRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = HybridRecord(
            record_id=str(uuid4()),
            who=who,
            what=what,
            when={"timestamp": now},
            where=where,
            why=why,
            how=how,
            state=state,
            proof=proof,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")
        return record

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
