"""Device-local approval queue for processes, deployments, and commits.

This module is intentionally notification-only: it never starts a process,
deploys an artifact, commits code, pushes a branch, or contacts a provider.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPROVAL_KINDS = frozenset({"PROCESS", "DEPLOYMENT", "COMMIT"})
APPROVAL_STATES = frozenset({"PENDING", "APPROVED", "DENIED", "EXPIRED", "CANCELLED"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(kind: str, subject: str, payload: dict[str, Any]) -> str:
    material = json.dumps(
        {"kind": kind, "subject": subject, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ApprovalStore:
    """Local JSONL-backed approval queue with auditable owner decisions."""

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
            if line.strip():
                record = json.loads(line)
                if record.get("approval_id"):
                    self._records[record["approval_id"]] = record

    def _persist(self) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            "".join(json.dumps(item, sort_keys=True) + "\n" for item in self._records.values()),
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
        timestamp = _now()
        with self._lock:
            for record in self._records.values():
                if record["fingerprint"] == fingerprint and record["state"] == "PENDING":
                    record["last_notified"] = timestamp
                    record["notification_count"] += 1
                    record["audit"].append({"event": "APPROVAL_RENOTIFIED", "timestamp": timestamp})
                    self._persist()
                    return json.loads(json.dumps(record))

            approval_id = fingerprint[:16]
            record = {
                "approval_id": approval_id,
                "fingerprint": fingerprint,
                "kind": kind,
                "subject": subject,
                "summary": summary,
                "requested_by": requested_by,
                "payload": payload,
                "state": "PENDING",
                "created_at": timestamp,
                "last_notified": timestamp,
                "notification_count": 1,
                "expires_at": expires_at,
                "audit": [{"event": "APPROVAL_REQUESTED", "timestamp": timestamp}],
            }
            self._records[approval_id] = record
            self._persist()
            return json.loads(json.dumps(record))

    def list(self, state: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            values = list(self._records.values())
            if state is not None:
                values = [item for item in values if item["state"] == state]
            if kind is not None:
                values = [item for item in values if item["kind"] == kind]
            return json.loads(json.dumps(values))

    def decide(self, approval_id: str, decision: str, owner: str) -> dict[str, Any]:
        if decision not in {"APPROVED", "DENIED", "EXPIRED", "CANCELLED"}:
            raise ValueError("decision must be APPROVED, DENIED, EXPIRED, or CANCELLED")
        if not owner.strip():
            raise ValueError("owner is required")
        with self._lock:
            record = self._records.get(approval_id)
            if record is None:
                raise KeyError(f"Unknown approval: {approval_id}")
            if record["state"] != "PENDING":
                raise ValueError(f"Approval is already {record['state']}")
            timestamp = _now()
            record["state"] = decision
            record["decided_at"] = timestamp
            record["decided_by"] = owner
            record["audit"].append({
                "event": f"APPROVAL_{decision}",
                "timestamp": timestamp,
                "owner": owner,
            })
            self._persist()
            return json.loads(json.dumps(record))
