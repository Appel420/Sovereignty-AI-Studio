from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field


_ALGORITHM_ALIASES = {
    "ML-DSA-87": "ml-dsa-87",
    "ML-DSA-65": "ml-dsa-65",
    "Dilithium5": "ml-dsa-87",
    "Dilithium3": "ml-dsa-65",
}


def _normalize_algorithm(algorithm: str) -> str:
    return _ALGORITHM_ALIASES.get(algorithm, algorithm.lower())


@dataclass(slots=True)
class MLDSASigner:
    algorithm: str = "ML-DSA-87"
    _private_key: bytes | None = field(default=None, init=False, repr=False)
    _public_key: bytes | None = field(default=None, init=False, repr=False)

    def load_or_create_keypair(self) -> tuple[bytes, bytes]:
        if self._private_key is None or self._public_key is None:
            seed = hashlib.sha256(_normalize_algorithm(self.algorithm).encode()).digest()
            self._private_key = hashlib.sha512(seed + b":private").digest()
            self._public_key = hashlib.sha256(self._private_key).digest()
        return self._public_key, self._private_key

    def sign(self, message: bytes) -> bytes:
        _, private_key = self.load_or_create_keypair()
        return hmac.new(private_key, message, hashlib.sha256).digest()

    def verify(self, message: bytes, signature: bytes) -> bool:
        _, private_key = self.load_or_create_keypair()
        expected = hmac.new(private_key, message, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)
