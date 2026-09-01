"""Local session authorization proof verification."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os


class SessionAuthorizationError(ValueError):
    """Raised when a session authorization proof cannot be verified."""


def verify_session_proof(proof: str) -> bool:
    """Verify a locally signed session proof."""
    raw = os.environ.get("SOVEREIGN_SESSION_SIGNING_KEY")
    if not raw:
        raise SessionAuthorizationError("session verification key unavailable")
    secret = raw.encode("utf-8")

    encoded_payload, encoded_signature = proof.split(".", 1)
    try:
        expected = hmac.new(
            secret, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        actual = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
    except (ValueError, TypeError, UnicodeEncodeError) as exc:
        raise SessionAuthorizationError("invalid session proof encoding") from exc

    if not hmac.compare_digest(expected, actual):
        raise SessionAuthorizationError("invalid session proof signature")
    return True
