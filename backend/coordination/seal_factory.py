from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from .hardware_seal import (
    DigestAlgorithm,
    HardwareSealResult,
    KeyReference,
    PayloadDigest,
    SealStrength,
    SignatureKind,
)


class HardwareUnavailable(Exception):
    """No usable hardware sealing backend is available."""


class HardwareSealError(Exception):
    """A hardware backend exists but failed while sealing."""


class HardwareBackend(Protocol):
    backend: str
    algorithm: str
    key: KeyReference
    device_reference: str

    def sign(self, payload: bytes) -> bytes:
        """Return a signature verifiable with the associated public key."""


@dataclass(frozen=True, slots=True)
class SealOutcome:
    result: HardwareSealResult
    fallback: bool

    def to_dict(self) -> dict[str, object]:
        value = self.result.to_dict()
        value["fallback"] = self.fallback
        return value


def _payload_hash(payload: bytes) -> PayloadDigest:
    return PayloadDigest.compute(payload, DigestAlgorithm.SHA3_512)


def _software_fallback(payload: bytes, *, previous_seal: bytes | None = None) -> SealOutcome:
    digest = _payload_hash(payload)
    result = HardwareSealResult(
        version=1,
        payload_digest=digest,
        signature_algorithm="SHA3-512-DIGEST",
        signature=digest.value,
        key=KeyReference("software-digest", "software"),
        strength=SealStrength.SOFTWARE,
        timestamp=datetime.now(timezone.utc).isoformat(),
        device_reference="software",
        previous_seal=previous_seal,
        signature_kind=SignatureKind.DIGEST,
    )
    return SealOutcome(result=result, fallback=True)


def seal_in_hardware(
    payload: bytes,
    *,
    backend: HardwareBackend | None = None,
    previous_seal: bytes | None = None,
) -> SealOutcome:
    """Seal with an injected hardware provider or use an explicit fallback."""
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")

    if backend is None:
        return _software_fallback(payload, previous_seal=previous_seal)

    try:
        signature = backend.sign(payload)
    except (HardwareUnavailable, HardwareSealError):
        return _software_fallback(payload, previous_seal=previous_seal)

    if not signature:
        return _software_fallback(payload, previous_seal=previous_seal)

    result = HardwareSealResult(
        version=1,
        payload_digest=_payload_hash(payload),
        signature_algorithm=backend.algorithm,
        signature=signature,
        key=backend.key,
        strength=SealStrength.HARDWARE_BACKED,
        timestamp=datetime.now(timezone.utc).isoformat(),
        device_reference=backend.device_reference,
        previous_seal=previous_seal,
        signature_kind=SignatureKind.SIGNATURE,
    )
    return SealOutcome(result=result, fallback=False)
