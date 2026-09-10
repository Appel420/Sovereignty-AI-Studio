"""Device-local approval queue for governed operations.

Owner decisions are recorded locally. Approval does not itself execute an
operation or grant unrestricted authority.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPROVAL_KINDS = frozenset({"PROCESS", "DEPLOYMENT", "COMMIT"})
DECISIONS = frozenset({"APPROVED", "DENIED", "EXPIRED", "CANCELLED", "HELD"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(kind: str, subject: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            {"kind": kind, "subject": subject, "payload": payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


class ApprovalStore:
    """Persistent, device-local owner decision records."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._records: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text("utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                self._records[record["approval_id"]] = record

    def _persist(self) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in self._records.values()),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def request(
        self,
        *,
        kind: str,
        subject: str,
        summary: str,
        requested_by: str,
        payload: dict[str, Any] | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        if kind not in APPROVAL_KINDS:
            raise ValueError(f"kind must be one of {sorted(APPROVAL_KINDS)}")
        payload = payload or {}
        fingerprint = _fingerprint(kind, subject, payload)
        now = _now()
        with self._lock:
            for record in self._records.values():
                if record["fingerprint"] == fingerprint and record["state"] == "PENDING":
                    record["last_notified"] = now
                    record["notification_count"] += 1
                    record["audit"].append({"event": "APPROVAL_RENOTIFIED", "timestamp": now})
                    self._persist()
                    return json.loads(json.dumps(record))
            record = {
                "approval_id": fingerprint[:16],
                "fingerprint": fingerprint,
                "kind": kind,
                "subject": subject,
                "summary": summary,
                "requested_by": requested_by,
                "payload": payload,
                "state": "PENDING",
                "created_at": now,
                "last_notified": now,
                "notification_count": 1,
                "expires_at": expires_at,
                "audit": [{"event": "APPROVAL_REQUESTED", "timestamp": now}],
            }
            self._records[record["approval_id"]] = record
            self._persist()
            return json.loads(json.dumps(record))

    def list(self, state: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())
            if state is not None:
                records = [record for record in records if record["state"] == state]
            if kind is not None:
                records = [record for record in records if record["kind"] == kind]
            return json.loads(json.dumps(records))

    def decide(self, approval_id: str, decision: str, owner: str) -> dict[str, Any]:
        if decision not in DECISIONS:
            raise ValueError("decision must be APPROVED, DENIED, EXPIRED, CANCELLED, or HELD")
        if not owner.strip():
            raise ValueError("owner is required")
        with self._lock:
            record = self._records.get(approval_id)
            if record is None:
                raise KeyError(f"Unknown approval: {approval_id}")
            if record["state"] != "PENDING":
                raise ValueError(f"Approval is already {record['state']}")
            now = _now()
            record.update(state=decision, decided_at=now, decided_by=owner)
            record["audit"].append(
                {"event": f"APPROVAL_{decision}", "timestamp": now, "owner": owner}
            )
            self._persist()
            return json.loads(json.dumps(record))
