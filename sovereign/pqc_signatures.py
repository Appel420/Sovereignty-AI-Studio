"""Compatibility ML-DSA signer shim for workflow imports.

This module provides a minimal signer API used by CI workflows when a full
post-quantum implementation is not available in this repository checkout.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field


@dataclass
class MLDSASigner:
    """Small compatibility signer with the same interface used in workflows."""

    algorithm: str = "ML-DSA-87"
    _secret_key: bytes = field(default=b"", init=False, repr=False)
    _public_key: bytes = field(default=b"", init=False, repr=False)

    def load_or_create_keypair(self) -> tuple[bytes, bytes]:
        if not self._secret_key:
            self._secret_key = secrets.token_bytes(32)
            self._public_key = hashlib.sha256(self._secret_key).digest()
        return self._public_key, self._secret_key

    def sign(self, message: bytes) -> bytes:
        _, secret_key = self.load_or_create_keypair()
        return hmac.new(secret_key, message, hashlib.sha256).digest()

    def verify(self, message: bytes, signature: bytes) -> bool:
        expected = self.sign(message)
        return hmac.compare_digest(expected, signature)
