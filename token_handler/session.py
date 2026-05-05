"""
SessionTokenManager — session token generation, rotation, and validation.

Session tokens are short-lived random tokens stored in-memory.
They are used to authenticate WebSocket connections from the frontend.

Usage:
    stm = SessionTokenManager()
    token = stm.create("user-42", role="admin")
    info = stm.validate(token)   # Returns session info dict or None
    stm.revoke(token)
"""

import hashlib
import logging
import os
import time
from typing import Any, Optional

log = logging.getLogger("token_handler.session")

_DEFAULT_TTL = 86400  # 24 hours in seconds


class SessionTokenManager:
    """In-memory session token store with TTL and rotation."""

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL) -> None:
        self._ttl = ttl_seconds
        # {token: {user_id, role, created, expires, meta}}
        self._sessions: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Create / rotate
    # ------------------------------------------------------------------

    def create(
        self,
        user_id: str,
        role: str = "user",
        meta: dict | None = None,
    ) -> str:
        """
        Generate a new session token for `user_id`.
        Returns the token string.
        """
        token = self._gen_token(user_id)
        now = int(time.time())
        self._sessions[token] = {
            "user_id": user_id,
            "role": role,
            "created": now,
            "expires": now + self._ttl,
            "meta": meta or {},
        }
        log.info("Session created for user=%s role=%s", user_id, role)
        return token

    def rotate(self, old_token: str) -> Optional[str]:
        """
        Issue a new token for the same session, revoke the old one.
        Returns the new token or None if the old token was invalid.
        """
        info = self.validate(old_token)
        if not info:
            log.warning("rotate() called with invalid token")
            return None
        self.revoke(old_token)
        new_token = self.create(info["user_id"], info["role"], info.get("meta"))
        log.info("Token rotated for user=%s", info["user_id"])
        return new_token

    # ------------------------------------------------------------------
    # Validate / lookup
    # ------------------------------------------------------------------

    def validate(self, token: str) -> Optional[dict[str, Any]]:
        """
        Validate a token. Returns session info dict on success,
        None if missing or expired.
        """
        if not token:
            return None
        info = self._sessions.get(token)
        if not info:
            return None
        if time.time() > info["expires"]:
            self._sessions.pop(token, None)
            log.debug("Token expired for user=%s", info.get("user_id"))
            return None
        return dict(info)

    def is_valid(self, token: str) -> bool:
        return self.validate(token) is not None

    # ------------------------------------------------------------------
    # Revoke
    # ------------------------------------------------------------------

    def revoke(self, token: str) -> bool:
        """Revoke a session token. Returns True if it existed."""
        existed = token in self._sessions
        self._sessions.pop(token, None)
        if existed:
            log.info("Token revoked")
        return existed

    def revoke_all(self, user_id: str) -> int:
        """Revoke all tokens for a given user_id. Returns count revoked."""
        to_remove = [
            t for t, info in self._sessions.items() if info["user_id"] == user_id
        ]
        for t in to_remove:
            del self._sessions[t]
        log.info("Revoked %d tokens for user=%s", len(to_remove), user_id)
        return len(to_remove)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def purge_expired(self) -> int:
        """Remove expired tokens. Returns count removed."""
        now = time.time()
        to_remove = [t for t, info in self._sessions.items() if now > info["expires"]]
        for t in to_remove:
            del self._sessions[t]
        if to_remove:
            log.debug("Purged %d expired sessions", len(to_remove))
        return len(to_remove)

    def active_count(self) -> int:
        """Return number of non-expired sessions."""
        self.purge_expired()
        return len(self._sessions)

    def status(self) -> dict[str, Any]:
        """Return a status summary (no tokens or user data)."""
        self.purge_expired()
        return {
            "active_sessions": len(self._sessions),
            "ttl_seconds": self._ttl,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _gen_token(user_id: str) -> str:
        """Generate a cryptographically random session token."""
        random_bytes = os.urandom(32)
        ts = str(time.time()).encode()
        uid = user_id.encode()
        digest = hashlib.sha256(random_bytes + ts + uid).hexdigest()
        return f"sgt_{digest}"
