"""Signed scope leases for repository write authorization (I9).

Issuance is local to the DevAssist420 coordinator process. Payload integrity uses
SHA3-512. The issuer MAC is HMAC-SHA3-512 with a local issuer key
(``SOVEREIGN_LEASE_ISSUER_KEY`` or a process-ephemeral key).

ML-DSA-87 (or ML-DSA-65) issuer signatures are the intended production upgrade:
keep the same canonical payload and ``payload_hash``; replace ``mac`` with a
PQC signature field without changing the write-gate API.

Writes must present a valid, non-expired lease whose scope covers the paths.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping

from .conflict_manager import scopes_overlap
from .task_envelope import TaskEnvelope


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def canonical_payload_bytes(payload: Mapping[str, object]) -> bytes:
    """Deterministic JSON (sorted keys, no whitespace variance)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def payload_hash(payload: Mapping[str, object]) -> str:
    digest = hashlib.sha3_512(canonical_payload_bytes(payload)).hexdigest()
    return f"sha3-512:{digest}"


def _load_issuer_key() -> bytes:
    raw = os.environ.get("SOVEREIGN_LEASE_ISSUER_KEY", "").strip()
    if raw:
        return raw.encode("utf-8")
    # Process-ephemeral key: valid within one coordinator lifetime only.
    return secrets.token_bytes(32)


@dataclass(frozen=True, slots=True)
class LeaseToken:
    lease_id: str
    task_id: str
    agent_id: str
    branch: str
    scope: tuple[str, ...]
    generation: int
    issued_at: str
    expires_at: str
    renewal_count: int
    issuer: str
    registry_hash: str
    payload_hash: str
    mac: str
    algorithm: str = "HMAC-SHA3-512"

    def payload_for_sign(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "branch": self.branch,
            "expires_at": self.expires_at,
            "generation": self.generation,
            "issued_at": self.issued_at,
            "issuer": self.issuer,
            "lease_id": self.lease_id,
            "registry_hash": self.registry_hash,
            "renewal_count": self.renewal_count,
            "scope": list(self.scope),
            "task_id": self.task_id,
        }

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["scope"] = list(self.scope)
        return data


class LeaseError(Exception):
    """Lease validation or issuance failure (fail closed)."""


class LeaseIssuer:
    """Issue, renew, verify, and gate writes under signed leases."""

    def __init(
        self,
        *,
        issuer_name: str = "devassist420-coordinator",
        default_ttl_seconds: int = 1800,
        registry_hash: str = "sha3-512:unspecified",
        issuer_key: bytes | None = None,
    ) -> None:
        pass  # placate type checkers if split; real init below

    def __init__(
        self,
        *,
        issuer_name: str = "devassist420-coordinator",
        default_ttl_seconds: int = 1800,
        registry_hash: str = "sha3-512:unspecified",
        issuer_key: bytes | None = None,
    ) -> None:
        self.issuer_name = issuer_name
        self.default_ttl_seconds = default_ttl_seconds
        self.registry_hash = registry_hash
        self._key = issuer_key if issuer_key is not None else _load_issuer_key()
        self._generations: dict[str, int] = {}
        self._active: dict[str, LeaseToken] = {}  # lease_id -> token
        self._by_task: dict[str, str] = {}  # task_id -> lease_id

    def _sign(self, payload: Mapping[str, object]) -> tuple[str, str]:
        body = canonical_payload_bytes(payload)
        digest = hashlib.sha3_512(body).hexdigest()
        ph = f"sha3-512:{digest}"
        mac = hmac.new(self._key, body, hashlib.sha3_512).hexdigest()
        return ph, f"hmac-sha3-512:{mac}"

    def _scope_key(self, scope: Iterable[str]) -> str:
        return "|".join(sorted(str(s) for s in scope))

    def issue(
        self,
        envelope: TaskEnvelope,
        *,
        agent_id: str,
        ttl_seconds: int | None = None,
    ) -> LeaseToken:
        if not envelope.branch:
            raise LeaseError("cannot issue lease without branch")
        if envelope.branch in {"main", "master", "collaboration"}:
            raise LeaseError(f"refusing lease on protected branch: {envelope.branch}")
        sk = self._scope_key(envelope.scope)
        gen = self._generations.get(sk, 0) + 1
        self._generations[sk] = gen
        now = _utc_now()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires = now + timedelta(seconds=ttl)
        lease_id = str(uuid.uuid4())
        provisional = {
            "agent_id": agent_id,
            "branch": envelope.branch,
            "expires_at": _iso(expires),
            "generation": gen,
            "issued_at": _iso(now),
            "issuer": self.issuer_name,
            "lease_id": lease_id,
            "registry_hash": self.registry_hash,
            "renewal_count": 0,
            "scope": list(envelope.scope),
            "task_id": envelope.task_id,
        }
        ph, mac = self._sign(provisional)
        token = LeaseToken(
            lease_id=lease_id,
            task_id=envelope.task_id,
            agent_id=agent_id,
            branch=envelope.branch,
            scope=tuple(envelope.scope),
            generation=gen,
            issued_at=provisional["issued_at"],  # type: ignore[arg-type]
            expires_at=provisional["expires_at"],  # type: ignore[arg-type]
            renewal_count=0,
            issuer=self.issuer_name,
            registry_hash=self.registry_hash,
            payload_hash=ph,
            mac=mac,
        )
        self._active[lease_id] = token
        self._by_task[envelope.task_id] = lease_id
        return token

    def renew(self, lease_id: str, *,
              ttl_seconds: int | None = None) -> LeaseToken:
        current = self._active.get(lease_id)
        if current is None:
            raise LeaseError("unknown or released lease")
        self.verify(current)
        now = _utc_now()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires = now + timedelta(seconds=ttl)
        provisional = {
            "agent_id": current.agent_id,
            "branch": current.branch,
            "expires_at": _iso(expires),
            "generation": current.generation,
            "issued_at": current.issued_at,
            "issuer": current.issuer,
            "lease_id": current.lease_id,
            "registry_hash": current.registry_hash,
            "renewal_count": current.renewal_count + 1,
            "scope": list(current.scope),
            "task_id": current.task_id,
        }
        ph, mac = self._sign(provisional)
        token = LeaseToken(
            lease_id=current.lease_id,
            task_id=current.task_id,
            agent_id=current.agent_id,
            branch=current.branch,
            scope=current.scope,
            generation=current.generation,
            issued_at=current.issued_at,
            expires_at=provisional["expires_at"],  # type: ignore[arg-type]
            renewal_count=current.renewal_count + 1,
            issuer=current.issuer,
            registry_hash=current.registry_hash,
            payload_hash=ph,
            mac=mac,
        )
        self._active[lease_id] = token
        return token

    def release(self, lease_id: str) -> None:
        token = self._active.pop(lease_id, None)
        if token is not None:
            self._by_task.pop(token.task_id, None)
            sk = self._scope_key(token.scope)
            # Generation stays elevated so stale tokens cannot be reused.
            self._generations[sk] = max(self._generations.get(sk, 0), token.generation)

    def release_task(self, task_id: str) -> None:
        lease_id = self._by_task.get(task_id)
        if lease_id:
            self.release(lease_id)

    def verify(self, token: LeaseToken) -> None:
        expected_ph, expected_mac = self._sign(token.payload_for_sign())
        if not hmac.compare_digest(token.payload_hash, expected_ph):
            raise LeaseError("payload hash mismatch")
        if not hmac.compare_digest(token.mac, expected_mac):
            raise LeaseError("lease MAC invalid")
        if token.registry_hash != self.registry_hash and self.registry_hash != "sha3-512:unspecified":
            # Allow unspecified issuer config; enforce when registry_hash is pinned.
            if token.registry_hash != self.registry_hash:
                raise LeaseError("registry hash mismatch")
        expires = datetime.fromisoformat(token.expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if _utc_now() >= expires:
            raise LeaseError("lease expired")
        active = self._active.get(token.lease_id)
        if active is None:
            raise LeaseError("lease not active (released or unknown)")
        if active.generation != token.generation:
            raise LeaseError("stale lease generation")

    def covers_paths(self, token: LeaseToken, paths: Iterable[str]) -> bool:
        path_list = [str(p) for p in paths]
        if not path_list:
            return False
        for path in path_list:
            if not any(scopes_overlap(path, s) or path == s for s in token.scope):
                # Tag-only scopes: exact membership required
                if path not in token.scope:
                    return False
        return True

    def require_for_write(self, token: LeaseToken | None, paths: Iterable[str]) -> LeaseToken:
        """I9: repository writes require a valid lease token covering paths."""
        if token is None:
            raise LeaseError("write rejected: missing lease token")
        self.verify(token)
        if not self.covers_paths(token, paths):
            raise LeaseError("write rejected: lease scope does not cover paths")
        return token
