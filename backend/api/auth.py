"""
Sovereignty AI Studio — Auth API
JWT authentication with optional Keycloak integration.
No external SaaS — fully self-hosted.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "change-me"))
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# ──────────────────────────────────────────────────────────────────────────
# Minimal JWT implementation (PyJWT if available, pure-Python fallback)
# ──────────────────────────────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    import base64
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def _sign_jwt(payload: Dict[str, Any]) -> str:
    """Create a signed HS256 JWT without external libraries."""
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url_encode(json.dumps(payload).encode())
    signing_input = f"{header}.{body}"
    sig = hmac.new(
        _JWT_SECRET.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def _verify_jwt(token: str) -> Dict[str, Any]:
    """Verify HS256 JWT and return payload, or raise ValueError."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWT")
    header_b64, body_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{body_b64}"
    expected_sig = hmac.new(
        _JWT_SECRET.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    provided_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Invalid JWT signature")
    payload = json.loads(_b64url_decode(body_b64))
    if "exp" in payload and time.time() > payload["exp"]:
        raise ValueError("JWT expired")
    return payload


# ──────────────────────────────────────────────────────────────────────────
# Public auth helpers
# ──────────────────────────────────────────────────────────────────────────

def create_token(user_id: str, email: str, role: str, org_id: Optional[str] = None) -> str:
    """Issue a signed JWT for a user."""
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + _EXPIRE_MINUTES * 60,
        "jti": str(uuid.uuid4()),
    }
    if org_id:
        payload["org_id"] = org_id

    try:
        import jwt as pyjwt  # type: ignore[import]
        return pyjwt.encode(payload, _JWT_SECRET, algorithm=_ALGORITHM)
    except ImportError:
        return _sign_jwt(payload)


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT and return its payload."""
    try:
        import jwt as pyjwt  # type: ignore[import]
        return pyjwt.decode(token, _JWT_SECRET, algorithms=[_ALGORITHM])
    except ImportError:
        return _verify_jwt(token)


def hash_password(plain: str) -> str:
    """Hash a password with bcrypt (or fallback SHA-256 if bcrypt unavailable)."""
    try:
        import bcrypt  # type: ignore[import]
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        logger.warning("bcrypt not installed; using SHA-256 fallback (not production-safe)")
        salt = os.urandom(16).hex()
        h = hashlib.sha256(f"{salt}{plain}".encode()).hexdigest()
        return f"sha256${salt}${h}"


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a stored hash."""
    try:
        import bcrypt  # type: ignore[import]
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ImportError:
        if hashed.startswith("sha256$"):
            _, salt, h = hashed.split("$", 2)
            return hmac.compare_digest(
                h, hashlib.sha256(f"{salt}{plain}".encode()).hexdigest()
            )
        return False


# ──────────────────────────────────────────────────────────────────────────
# User management helpers
# ──────────────────────────────────────────────────────────────────────────

def register_user(email: str, password: str, display_name: Optional[str] = None) -> dict:
    """Create a new user record (hashed password stored locally)."""
    from db.connector import execute_one

    existing = execute_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        raise ValueError(f"User with email {email!r} already exists")

    row = execute_one(
        """
        INSERT INTO users (email, password_hash, display_name)
        VALUES (%s, %s, %s)
        RETURNING id, email, display_name, role, created_at
        """,
        (email, hash_password(password), display_name),
    )
    if row is None:
        raise RuntimeError("Failed to create user")
    return dict(row)


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate a user by email/password. Returns user dict or None."""
    from db.connector import execute_one

    row = execute_one(
        "SELECT id, email, display_name, role, password_hash "
        "FROM users WHERE email = %s AND active = TRUE",
        (email,),
    )
    if row is None:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    user = {k: v for k, v in row.items() if k != "password_hash"}
    return user


def get_user_by_id(user_id: str) -> Optional[dict]:
    from db.connector import execute_one

    row = execute_one(
        "SELECT id, email, display_name, role, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    return dict(row) if row else None
