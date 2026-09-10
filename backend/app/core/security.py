# app/core/security.py
from datetime import datetime, timedelta
import hashlib
from hmac import compare_digest
from typing import Any, Optional

import jwt
from jwt import InvalidTokenError

from app.config import settings

bcrypt: Any | None = None
try:
    import bcrypt as _bcrypt  # type: ignore[import]
except ImportError:  # pragma: no cover - exercised only when bcrypt is unavailable
    pass
else:
    bcrypt = _bcrypt

_BCRYPT_SHA256_PREFIX = "bcrypt_sha256$"


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = (
        datetime.utcnow() + expires_delta
        if expires_delta
        else datetime.utcnow()
        + timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed version."""
    if hashed_password.startswith(_BCRYPT_SHA256_PREFIX):
        if bcrypt is None:
            return False
        try:
            return bcrypt.checkpw(
                _password_digest(plain_password),
                hashed_password[len(_BCRYPT_SHA256_PREFIX) :].encode(),
            )
        except ValueError:
            return False

    if hashed_password.startswith("sha256$"):
        try:
            _, salt, digest = hashed_password.split("$", 2)
        except ValueError:
            return False
        return compare_digest(
            digest,
            hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest(),
        )

    if bcrypt is None:
        return False

    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    if bcrypt is None:
        salt = hashlib.sha256(password.encode()).hexdigest()[:16]
        digest = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"sha256${salt}${digest}"

    return (
        f"{_BCRYPT_SHA256_PREFIX}"
        f"{bcrypt.hashpw(_password_digest(password), bcrypt.gensalt()).decode()}"
    )


def _password_digest(password: str) -> bytes:
    """Normalize passwords before bcrypt hashing to avoid the 72-byte limit."""
    return hashlib.sha256(password.encode()).digest()


def verify_token(token: str) -> Optional[str]:
    """Validate JWT and return subject (username) if valid."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload.get("sub")
    except InvalidTokenError:
        return None
