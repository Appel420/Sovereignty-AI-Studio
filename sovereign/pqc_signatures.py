"""Fail-closed ML-DSA signing through the locally installed liboqs provider.

This module deliberately does not emulate post-quantum signatures.  Install
the locally packaged ``oqs`` binding (liboqs-python plus liboqs) before using
this functionality in a production workflow.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class PQCUnavailableError(RuntimeError):
    """Raised when a real local liboqs ML-DSA implementation is unavailable."""


_ALGORITHM_ALIASES = {
    "ML-DSA-65": "ML-DSA-65",
    "ML-DSA-87": "ML-DSA-87",
    "Dilithium3": "ML-DSA-65",
    "Dilithium5": "ML-DSA-87",
}


def _load_oqs():
    try:
        import oqs  # type: ignore[import-not-found]
    except ImportError as error:
        raise PQCUnavailableError(
            "Real ML-DSA requires a local liboqs-python installation; "
            "no HMAC or simulated fallback is permitted."
        ) from error
    return oqs


@dataclass(slots=True)
class MLDSASigner:
    """ML-DSA signer backed solely by a locally installed liboqs provider."""

    algorithm: str = "ML-DSA-65"
    _secret_key: bytes | None = field(default=None, init=False, repr=False)
    _public_key: bytes | None = field(default=None, init=False, repr=False)

    @property
    def oqs_algorithm(self) -> str:
        try:
            return _ALGORITHM_ALIASES[self.algorithm]
        except KeyError as error:
            raise ValueError(f"Unsupported ML-DSA algorithm: {self.algorithm}") from error

    def load_or_create_keypair(self) -> tuple[bytes, bytes]:
        if self._public_key is None or self._secret_key is None:
            oqs = _load_oqs()
            with oqs.Signature(self.oqs_algorithm) as signer:
                self._public_key = signer.generate_keypair()
                self._secret_key = signer.export_secret_key()
        return self._public_key, self._secret_key

    def sign(self, message: bytes) -> bytes:
        _, secret_key = self.load_or_create_keypair()
        oqs = _load_oqs()
        with oqs.Signature(self.oqs_algorithm, secret_key) as signer:
            return signer.sign(message)

    def verify(self, message: bytes, signature: bytes) -> bool:
        public_key, _ = self.load_or_create_keypair()
        oqs = _load_oqs()
        with oqs.Signature(self.oqs_algorithm) as verifier:
            return bool(verifier.verify(message, signature, public_key))
