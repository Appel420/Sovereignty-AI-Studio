"""Cryptographic primitives for the Black Canary store.

The suite is deliberately explicit and fail-closed.  BLAKE3 is required;
there is no silent hash downgrade.
"""
from __future__ import annotations

from typing import Final

import blake3
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

BLACK_CANARY_SUITE: Final[str] = "black-canary-pq-2026"
BLAKE3_DOMAIN: Final[bytes] = b"sovereignty-ai/black-canary/blake3/v1/"
HKDF_INFO: Final[bytes] = b"sovereignty-ai/black-canary/aes-kw-kek/v1"


def blake3_digest(data: bytes, *, domain: bytes = BLAKE3_DOMAIN) -> bytes:
    """Return a domain-separated BLAKE3 digest."""
    if not isinstance(data, bytes) or not isinstance(domain, bytes):
        raise TypeError("data and domain must be bytes")
    return blake3.blake3(domain + data).digest()


def derive_kek(master_key: bytes, *, salt: bytes, context: bytes = b"") -> bytes:
    """Derive a 256-bit AES-KW key using HKDF-SHA256."""
    if len(master_key) < 32:
        raise ValueError("master_key must contain at least 32 bytes")
    if not salt:
        raise ValueError("salt must not be empty")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=HKDF_INFO + context,
    ).derive(master_key)


def argon2id_derive(
    password: bytes | str,
    *,
    salt: bytes,
    length: int = 32,
    time_cost: int = 3,
    memory_cost: int = 64 * 1024,
    parallelism: int = 2,
) -> bytes:
    """Derive a key with Argon2id and explicit parameters."""
    if isinstance(password, str):
        password = password.encode("utf-8")
    if not isinstance(password, bytes) or len(password) == 0:
        raise ValueError("password must not be empty")
    if len(salt) < 16:
        raise ValueError("salt must contain at least 16 bytes")
    if length < 16 or time_cost < 1 or memory_cost < 8 * parallelism:
        raise ValueError("invalid Argon2id parameters")
    return hash_secret_raw(
        secret=password,
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=length,
        type=Type.ID,
    )
