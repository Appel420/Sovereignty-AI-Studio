"""Device-local deduplicated issue suggestions.

This module intentionally has no network, GitHub, provider, or cloud dependency.
It turns repeated runtime observations into one owner-reviewable suggestion.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_STATES = frozenset({"PROPOSED", "ACCEPTED", "DECLINED", "DEFERRED", "RESOLVED"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"0x[0-9a-f]+|[0-9a-f]{8,}", "<id>", text)
    return text


def suggestion_fingerprint(
    *,
    category: str,
    reason: str,
    source: str = "",
    component: str = "",
    target: str = "",
    mode: str = "",
) -> str:
    """Return a stable local fingerprint for one normalized observation."""
    material = "|".join(
        _normalize(value)
        for value in (category, reason, source, component, target, mode)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class IssueSuggestionStore:
    """Append-only-ish JSONL store with explicit owner state transitions."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._records: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            fingerprint = record.get("fingerprint")
            if fingerprint:
                self._records[fingerprint] = record

    def _persist(self) -> None:
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        lines = "".join(json.dumps(record, sort_keys=True) + "\n" for record in self._records.values())
        temp.write_text(lines, encoding="utf-8")
        temp.replace(self.path)

    def observe(
        self,
        *,
        category: str,
        reason: str,
        title: str,
        evidence: str,
        source: str = "",
        component: str = "",
        target: str = "",
        mode: str = "offline",
        recommended_action: str = "Review the evidence and choose an owner decision.",
    ) -> dict[str, Any]:
        """Create or update one deduplicated suggestion."""
        fingerprint = suggestion_fingerprint(
            category=category,
            reason=reason,
            source=source,
            component=component,
            target=target,
            mode=mode,
        )
        timestamp = _now()
        with self._lock:
            record = self._records.get(fingerprint)
            if record is None:
                record = {
                    "suggestion_id": fingerprint[:16],
                    "fingerprint": fingerprint,
                    "state": "PROPOSED",
                    "category": category,
                    "title": title,
                    "reason": reason,
                    "evidence": [evidence],
                    "source": source,
                    "component": component,
                    "target": target,
                    "mode": mode,
                    "recommended_action": recommended_action,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "occurrences": 1,
                    "owner_decision": "PENDING",
                    "audit": [
                        {
                            "event": "ISSUE_SUGGESTION_PROPOSED",
                            "timestamp": timestamp,
                            "owner_action": False,
                        }
                    ],
                }
                self._records[fingerprint] = record
            else:
                record["last_seen"] = timestamp
                record["occurrences"] = int(record.get("occurrences", 0)) + 1
                if evidence not in record.setdefault("evidence", []):
                    record["evidence"].append(evidence)
                record.setdefault("audit", []).append(
                    {
                        "event": "ISSUE_SUGGESTION_DEDUPED",
                        "timestamp": timestamp,
                        "owner_action": False,
                    }
                )
            self._persist()
            return json.loads(json.dumps(record))

    def list(self, state: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())
            if state is not None:
                records = [record for record in records if record.get("state") == state]
            return json.loads(json.dumps(records))

    def decide(self, suggestion_id: str, decision: str) -> dict[str, Any]:
        """Apply an explicit owner decision; no automatic issue is created."""
        if decision not in {"ACCEPTED", "DECLINED", "DEFERRED", "RESOLVED"}:
            raise ValueError("decision must be ACCEPTED, DECLINED, DEFERRED, or RESOLVED")
        with self._lock:
            record = next(
                (item for item in self._records.values() if item.get("suggestion_id") == suggestion_id),
                None,
            )
            if record is None:
                raise KeyError(f"Unknown issue suggestion: {suggestion_id}")
            timestamp = _now()
            record["state"] = decision
            record["owner_decision"] = decision
            record.setdefault("audit", []).append(
                {
                    "event": f"ISSUE_SUGGESTION_{decision}",
                    "timestamp": timestamp,
                    "owner_action": True,
                }
            )
            self._persist()
            return json.loads(json.dumps(record))
