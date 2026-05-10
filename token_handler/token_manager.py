"""
token_handler/token_manager.py
===============================
Centralised JWT token management for Sovereignty AI Studio.

All token operations — issue, validate, refresh, revoke — live here.
The manager is intentionally dependency-light: it uses ``pyjwt`` (already in
requirements.txt) and Python stdlib only.

Security notes
--------------
- Tokens are signed with HMAC-SHA256 by default.
- The signing secret is read from the ``JWT_SECRET`` environment variable.
  **Never hard-code the secret.**
- Revoked tokens are tracked in an in-process set (``_revoked_jti``) and
  optionally persisted to a SQLite table so reboots do not re-allow them.
- Token rotation: :meth:`TokenManager.refresh` issues a new token and
  immediately revokes the old one.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional PyJWT dependency
# ---------------------------------------------------------------------------
try:
    import jwt  # PyJWT

    _JWT_OK = True
except ImportError:
    _JWT_OK = False
    log.warning(
        "PyJWT not installed — TokenManager will run in no-op mode. "
        "Install with: pip install pyjwt"
    )

# ---------------------------------------------------------------------------
# Configuration via environment
# ---------------------------------------------------------------------------
_DEFAULT_ALGORITHM = "HS256"
_DEFAULT_ACCESS_TTL_SECONDS = int(
    os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
) * 60  # convert minutes → seconds
_DEFAULT_REFRESH_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
_ISSUER = "sovereignty-ai-studio"


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------
class TokenError(Exception):
    """Raised when token validation fails for any reason."""


@dataclass
class TokenClaims:
    """Parsed, validated claims from a JWT.

    Attributes:
        subject:    Identity of the token holder (e.g. ``"user:alice"``).
        jti:        Unique JWT ID used for revocation tracking.
        scopes:     List of permission scopes granted to this token.
        issued_at:  Unix timestamp when the token was issued.
        expires_at: Unix timestamp when the token expires.
        extra:      Any additional claims that were embedded in the token.
    """

    subject: str
    jti: str
    scopes: List[str]
    issued_at: float
    expires_at: float
    extra: Dict = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Return True if the token has passed its expiry time."""
        return time.time() > self.expires_at

    @property
    def seconds_until_expiry(self) -> float:
        """Seconds remaining until expiry (negative if already expired)."""
        return self.expires_at - time.time()


# ---------------------------------------------------------------------------
# Token Manager
# ---------------------------------------------------------------------------
class TokenManager:
    """Issue, validate, refresh, and revoke JWT tokens.

    Args:
        secret:            HMAC signing secret.  Defaults to the
                           ``JWT_SECRET`` environment variable.
        algorithm:         JWT signing algorithm.  Defaults to ``HS256``.
        access_ttl:        Access token lifetime in seconds.
        refresh_ttl:       Refresh token lifetime in seconds.
        revocation_db:     Optional path to an SQLite file used to persist
                           revoked token JTIs across restarts.  When omitted
                           the revocation list is in-process only (lost on
                           restart).

    Example::

        tm = TokenManager()
        access_token = tm.issue("user:bob", scopes=["read"])
        claims = tm.validate(access_token)
        new_token = tm.refresh(access_token)
    """

    def __init__(
        self,
        secret: Optional[str] = None,
        algorithm: str = _DEFAULT_ALGORITHM,
        access_ttl: int = _DEFAULT_ACCESS_TTL_SECONDS,
        refresh_ttl: int = _DEFAULT_REFRESH_TTL_SECONDS,
        revocation_db: Optional[str] = None,
    ) -> None:
        self._secret = secret or os.environ.get("JWT_SECRET", "")
        if not self._secret:
            raise ValueError(
                "JWT_SECRET is not set.  Set the JWT_SECRET environment variable "
                "or pass `secret=` explicitly.  Operating with an empty HMAC key "
                "removes all signature security and is not permitted."
            )
        self._algorithm = algorithm
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        # In-process revocation set (JTI → expiry timestamp)
        self._revoked_jti: Dict[str, float] = {}
        self._revocation_db = revocation_db
        if revocation_db:
            self._init_revocation_db(revocation_db)
            self._load_revoked_from_db(revocation_db)

    # ------------------------------------------------------------------
    # Issue
    # ------------------------------------------------------------------

    def issue(
        self,
        subject: str,
        *,
        scopes: Optional[List[str]] = None,
        ttl: Optional[int] = None,
        extra_claims: Optional[Dict] = None,
    ) -> str:
        """Issue a signed JWT access token.

        Args:
            subject:      Identity to embed (e.g. ``"user:alice"``).
            scopes:       Permission scopes (e.g. ``["read", "ai_chat"]``).
            ttl:          Token lifetime in seconds.  Defaults to
                          :attr:`access_ttl`.
            extra_claims: Additional claims to embed in the payload.

        Returns:
            Signed JWT string.

        Raises:
            RuntimeError: If PyJWT is not installed.
        """
        if not _JWT_OK:
            raise RuntimeError("PyJWT is not installed.")

        now = time.time()
        lifetime = ttl if ttl is not None else self.access_ttl
        jti = str(uuid.uuid4())

        payload: Dict = {
            "sub": subject,
            "iss": _ISSUER,
            "iat": int(now),
            "exp": int(now + lifetime),
            "jti": jti,
            "scopes": scopes or [],
        }
        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        log.debug("Issued token for subject '%s' (jti=%s)", subject, jti)
        return token

    def issue_refresh_token(
        self, subject: str, *, scopes: Optional[List[str]] = None
    ) -> str:
        """Issue a long-lived refresh token.

        Refresh tokens have the ``token_type: refresh`` claim set so they
        can be distinguished from access tokens at validation time.
        """
        return self.issue(
            subject,
            scopes=scopes,
            ttl=self.refresh_ttl,
            extra_claims={"token_type": "refresh"},
        )

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate(self, token: str) -> TokenClaims:
        """Decode and validate a JWT token.

        Performs the following checks in order:
        1. Signature verification
        2. Expiry check (``exp`` claim)
        3. Issuer check (``iss`` claim)
        4. Revocation check (JTI in revoked set)

        Args:
            token: The raw JWT string.

        Returns:
            Parsed :class:`TokenClaims`.

        Raises:
            :class:`TokenError`: If validation fails for any reason.
        """
        if not _JWT_OK:
            raise TokenError("PyJWT is not installed.")

        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=_ISSUER,
                options={"require": ["exp", "iat", "sub", "jti"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenError("Token has expired.") from exc
        except jwt.InvalidIssuerError as exc:
            raise TokenError("Token issuer is invalid.") from exc
        except jwt.InvalidTokenError as exc:
            raise TokenError(f"Token is invalid: {exc}") from exc

        jti = payload.get("jti", "")
        if self._is_revoked(jti):
            raise TokenError("Token has been revoked.")

        return TokenClaims(
            subject=payload["sub"],
            jti=jti,
            scopes=payload.get("scopes", []),
            issued_at=float(payload["iat"]),
            expires_at=float(payload["exp"]),
            extra={
                k: v
                for k, v in payload.items()
                if k not in {"sub", "iss", "iat", "exp", "jti", "scopes"}
            },
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(
        self,
        refresh_token: str,
        *,
        new_scopes: Optional[List[str]] = None,
    ) -> str:
        """Exchange a valid refresh token for a new access token.

        The old token's JTI is revoked immediately so replay is impossible.

        Args:
            refresh_token: A previously issued refresh token.
            new_scopes:    Override scopes for the new token.  When ``None``
                           the original scopes are preserved.

        Returns:
            A new signed JWT access token string.

        Raises:
            :class:`TokenError`: If the refresh token is invalid or revoked.
        """
        claims = self.validate(refresh_token)

        if claims.extra.get("token_type") != "refresh":
            raise TokenError(
                "Provided token is not a refresh token. "
                "Only refresh tokens may be used to obtain new access tokens."
            )

        # Revoke the consumed refresh token
        self.revoke(claims.jti, expiry=claims.expires_at)

        return self.issue(
            claims.subject,
            scopes=new_scopes if new_scopes is not None else claims.scopes,
        )

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------

    def revoke(self, jti: str, *, expiry: Optional[float] = None) -> None:
        """Revoke a token by its JTI.

        Args:
            jti:    JWT ID to revoke.
            expiry: Token expiry timestamp.  Used to auto-prune stale entries
                    from the revocation list.  Defaults to ``now + access_ttl``.
        """
        exp = expiry or (time.time() + self.access_ttl)
        self._revoked_jti[jti] = exp
        if self._revocation_db:
            self._persist_revocation(jti, exp)
        log.debug("Revoked JTI %s", jti)

    def revoke_token(self, token: str) -> None:
        """Revoke a token by decoding it to extract its JTI.

        Unlike :meth:`revoke`, this method accepts the raw JWT string and
        verifies the signature (to prevent DoS via crafted JTIs) but ignores
        token expiry — the goal is to mark the JTI as revoked regardless of
        whether the token has already expired.
        """
        if not _JWT_OK:
            return
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"verify_exp": False},
            )
            jti = payload.get("jti", "")
            exp = float(payload.get("exp", time.time() + self.access_ttl))
            if jti:
                self.revoke(jti, expiry=exp)
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not decode token for revocation: %s", exc)

    def _is_revoked(self, jti: str) -> bool:
        """Check whether *jti* is in the revocation set (also prunes expired entries)."""
        self._prune_revoked()
        return jti in self._revoked_jti

    def _prune_revoked(self) -> None:
        """Remove entries whose associated tokens have already expired."""
        now = time.time()
        stale = [jti for jti, exp in self._revoked_jti.items() if exp < now]
        for jti in stale:
            del self._revoked_jti[jti]

    # ------------------------------------------------------------------
    # Persistence helpers (SQLite)
    # ------------------------------------------------------------------

    @staticmethod
    def _init_revocation_db(db_path: str) -> None:
        """Ensure the revocation table exists."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS revoked_tokens "
            "(jti TEXT PRIMARY KEY, expires_at REAL NOT NULL)"
        )
        conn.commit()
        conn.close()

    def _load_revoked_from_db(self, db_path: str) -> None:
        """Load non-expired revocations from the database into the in-process set."""
        now = time.time()
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT jti, expires_at FROM revoked_tokens WHERE expires_at > ?", (now,)
        ).fetchall()
        conn.close()
        for jti, exp in rows:
            self._revoked_jti[jti] = exp
        log.debug("Loaded %d revoked tokens from DB", len(rows))

    def _persist_revocation(self, jti: str, expiry: float) -> None:
        """Persist a revocation entry to the SQLite database."""
        if not self._revocation_db:
            return
        try:
            conn = sqlite3.connect(self._revocation_db)
            conn.execute(
                "INSERT OR REPLACE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
                (jti, expiry),
            )
            conn.commit()
            conn.close()
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not persist revocation to DB: %s", exc)
