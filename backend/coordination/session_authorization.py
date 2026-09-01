"""Signed session authorization for unprivileged AI consumers.

The assistant must receive a session proof issued by the local authority. A
session id, agent label, branch name, or environment variable is never treated
as proof of authority.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass


class SessionAuthorizationError(ValueError):
    """Raised when a session proof is absent, invalid, or expired."""


@dataclass(frozen=True, slots=True)
class SessionAuthorization:
    session_id: str
    identity_id: str
    capabilities: frozenset[str]
    branch: str | None
    mode: str
    expires_at: int

    def allows(self, capability: str) -> bool:
        return capability in self.capabilities


def verify_session_proof(
    proof: str,
    *,
    secret: bytes | None = None,
    now: int | None = None,
) -> SessionAuthorization:
    """Verify a locally issued HMAC-signed session proof.

    Format: base64url(payload-json).base64url(signature), where the signature
    is HMAC-SHA256 over the exact encoded payload. The signing secret must be
    supplied by the local authority; this function never creates one.
    """
    if not proof or "." not in proof:
        raise SessionAuthorizationError("missing or malformed session proof")
    if secret is None:
        raw = os.environ.get("SOVEREIGN_SESSION_SIGNING_KEY")
        if not raw:
            raise SessionAuthorizationError("session verification key unavailable")
        secret = raw.encode("utf-8")

    encoded_payload, encoded_signature = proof.split(".", 1)
    try:
        expected = hmac.new(secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
        try:
            actual = base64.urlsafe_b64decode(
                encoded_signature + "=" * (-len(encoded_signature) % 4), validate=True
            )
        except TypeError:
            actual = base64.urlsafe_b64decode(
                encoded_signature + "=" * (-len(encoded_signature) % 4)
            )
        if not hmac.compare_digest(expected, actual):
            raise SessionAuthorizationError("invalid session proof signature")
        try:
            decoded_payload = base64.urlsafe_b64decode(
                encoded_payload + "=" * (-len(encoded_payload) % 4), validate=True
            )
        except TypeError:
            decoded_payload = base64.urlsafe_b64decode(
                encoded_payload + "=" * (-len(encoded_payload) % 4)
            )
        payload = json.loads(decoded_payload)
    except SessionAuthorizationError:
        raise
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise SessionAuthorizationError("invalid session proof encoding") from exc

    required = {"session_id", "identity_id", "capabilities", "mode", "expires_at"}
    if not required.issubset(payload):
        raise SessionAuthorizationError("session proof missing required claims")

    current = int(time.time()) if now is None else now
    if int(payload["expires_at"]) <= current:
        raise SessionAuthorizationError("session proof expired")
    if payload["mode"] not in {"offline", "hybrid", "online"}:
        raise SessionAuthorizationError("unsupported session mode")
    if not isinstance(payload["capabilities"], list):
        raise SessionAuthorizationError("invalid capability claims")

    return SessionAuthorization(
        session_id=str(payload["session_id"]),
        identity_id=str(payload["identity_id"]),
        capabilities=frozenset(str(item) for item in payload["capabilities"]),
        branch=str(payload["branch"]) if payload.get("branch") else None,
        mode=str(payload["mode"]),
        expires_at=int(payload["expires_at"]),
    )
