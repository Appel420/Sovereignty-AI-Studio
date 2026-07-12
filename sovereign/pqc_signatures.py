"""Real ML-DSA-87 signer backed by the Open Quantum Safe liboqs-python library.

Fail-closed design: every method raises PQCUnavailableError immediately when
liboqs-python is not installed.  No HMAC, simulation, or other fallback is
ever performed – doing so would silently undermine the post-quantum security
guarantee this module is meant to provide.

Install the provider:
    pip install liboqs-python
or add the ``pqc`` optional dependency group:
    pip install -e ".[pqc]"
"""
from __future__ import annotations

from dataclasses import dataclass, field


class PQCUnavailableError(RuntimeError):
    """Raised when the liboqs post-quantum provider is not available."""


def _load_oqs() -> object:
    """Return the ``oqs`` module or raise PQCUnavailableError.

    The import is deferred so that the module can be loaded without liboqs;
    the error is only raised when an actual signing operation is attempted.
    """
    try:
        import oqs  # type: ignore[import-not-found, import-untyped]

        return oqs
    except ImportError as error:
        raise PQCUnavailableError(
            "Real ML-DSA requires a local liboqs-python installation; "
            "no HMAC or simulated fallback is permitted.  "
            "Install with: pip install liboqs-python"
        ) from error


@dataclass(slots=True)
class MLDSASigner:
    """Real ML-DSA-87 signer.

    Keypairs are generated lazily on first use and cached in-memory for the
    lifetime of the instance.  All operations are fail-closed: if liboqs is
    not available, PQCUnavailableError is raised rather than silently falling
    back to a weaker primitive.
    """

    algorithm: str = "ML-DSA-87"
    _public_key: bytes | None = field(default=None, init=False, repr=False)
    _secret_key: bytes | None = field(default=None, init=False, repr=False)

    def load_or_create_keypair(self) -> tuple[bytes, bytes]:
        """Return ``(public_key, secret_key)``, generating a new pair if needed."""
        if self._public_key is None or self._secret_key is None:
            oqs = _load_oqs()
            sig = oqs.Signature(self.algorithm)  # type: ignore[attr-defined]
            try:
                self._public_key = sig.generate_keypair()
                self._secret_key = sig.export_secret_key()
            finally:
                sig.free()
        return self._public_key, self._secret_key

    def sign(self, message: bytes) -> bytes:
        """Sign *message* with ML-DSA-87 and return the raw signature bytes."""
        oqs = _load_oqs()
        _, secret_key = self.load_or_create_keypair()
        sig = oqs.Signature(  # type: ignore[attr-defined]
            self.algorithm, secret_key=secret_key
        )
        try:
            return sig.sign(message)  # type: ignore[no-any-return]
        finally:
            sig.free()

    def verify(self, message: bytes, signature: bytes) -> bool:
        """Return True iff *signature* is a valid ML-DSA-87 signature of *message*."""
        oqs = _load_oqs()
        public_key, _ = self.load_or_create_keypair()
        sig = oqs.Signature(self.algorithm)  # type: ignore[attr-defined]
        try:
            return bool(sig.verify(message, signature, public_key))
        finally:
            sig.free()
