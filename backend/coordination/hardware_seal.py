"""Versioned, provenance-aware hardware seal contracts.

This module defines interfaces and verification rules only. It does not claim
that Secure Enclave, TPM, SGX, TrustZone, PQC, or any other hardware backend is
available. A provider must supply real evidence before a result can be marked
hardware-backed or hardware-attested.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Protocol, Sequence


CHAIN_RECORD_VERSION = 1


class SealStrength(str, Enum):
    SOFTWARE = "software"
    HARDWARE_BACKED = "hardware_backed"
    HARDWARE_ATTESTED = "hardware_attested"


class DigestAlgorithm(str, Enum):
    SHA256 = "sha256"
    SHA3_512 = "sha3-512"


class SealFailure(str, Enum):
    DIGEST_MISMATCH = "digest_mismatch"
    SIGNATURE_INVALID = "signature_invalid"
    UNKNOWN_KEY = "unknown_key"
    UNSUPPORTED_DIGEST = "unsupported_digest"
    UNSUPPORTED_SIGNATURE = "unsupported_signature"
    MISSING_ATTESTATION = "missing_attestation"
    INVALID_ATTESTATION = "invalid_attestation"
    CHAIN_LINK_INVALID = "chain_link_invalid"
    RECORD_VERSION_UNSUPPORTED = "record_version_unsupported"
    STRENGTH_EVIDENCE_MISMATCH = "strength_evidence_mismatch"
    INVALID_TIMESTAMP = "invalid_timestamp"


@dataclass(frozen=True, slots=True)
class PayloadDigest:
    algorithm: DigestAlgorithm
    value: bytes

    @classmethod
    def compute(
        cls,
        payload: bytes,
        algorithm: DigestAlgorithm = DigestAlgorithm.SHA3_512,
    ) -> "PayloadDigest":
        if algorithm is DigestAlgorithm.SHA256:
            value = hashlib.sha256(payload).digest()
        elif algorithm is DigestAlgorithm.SHA3_512:
            value = hashlib.sha3_512(payload).digest()
        else:  # pragma: no cover - protected by enum typing
            raise ValueError(f"unsupported digest algorithm: {algorithm}")
        return cls(algorithm=algorithm, value=value)

    def matches(self, payload: bytes) -> bool:
        return self == self.compute(payload, self.algorithm)

    def to_dict(self) -> dict[str, str]:
        return {"algorithm": self.algorithm.value, "value": self.value.hex()}


@dataclass(frozen=True, slots=True)
class KeyReference:
    key_id: str
    backend: str

    def __post_init__(self) -> None:
        if not self.key_id.strip():
            raise ValueError("key_id is required")
        if not self.backend.strip():
            raise ValueError("key backend is required")

    def to_dict(self) -> dict[str, str]:
        return {"key_id": self.key_id, "backend": self.backend}


@dataclass(frozen=True, slots=True)
class AttestationEvidence:
    """Platform evidence returned by a real attestation provider.

    ``verified`` is not self-authorizing. The independent verifier decides
    whether the evidence is valid for the requested strength.
    """

    provider: str
    evidence: bytes
    verified: bool = False
    source: str = "UNVERIFIED"

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("attestation provider is required")
        if not self.source.strip():
            raise ValueError("attestation source is required")


@dataclass(frozen=True, slots=True)
class HardwareSealResult:
    version: int
    payload_digest: PayloadDigest
    signature_algorithm: str
    signature: bytes
    key: KeyReference
    strength: SealStrength
    timestamp: str
    device_reference: str
    previous_seal: bytes | None = None
    attestation: AttestationEvidence | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("seal version must be positive")
        if not self.signature_algorithm.strip():
            raise ValueError("signature algorithm is required")
        if not self.signature:
            raise ValueError("signature is required")
        if not self.device_reference.strip():
            raise ValueError("device_reference is required")
        _parse_timestamp(self.timestamp)

    def to_dict(self) -> dict[str, object]:
        attestation: dict[str, object] | None = None
        if self.attestation is not None:
            attestation = {
                "provider": self.attestation.provider,
                "evidence": self.attestation.evidence.hex(),
                "verified": self.attestation.verified,
                "source": self.attestation.source,
            }
        return {
            "version": self.version,
            "payload_hash": self.payload_digest.to_dict(),
            "signature_algorithm": self.signature_algorithm,
            "signature": self.signature.hex(),
            "key": self.key.to_dict(),
            "strength": self.strength.value,
            "previous_seal": self.previous_seal.hex() if self.previous_seal else None,
            "timestamp": self.timestamp,
            "device_reference": self.device_reference,
            "attestation": attestation,
        }

    @property
    def record_hash(self) -> bytes:
        """Stable hash of the serialized record metadata."""
        encoded = repr(sorted(self.to_dict().items())).encode("utf-8")
        return hashlib.sha256(encoded).digest()


@dataclass(frozen=True, slots=True)
class VerificationResult:
    valid: bool
    strength_verified: SealStrength | None
    failure: SealFailure | None = None
    evidence_source: str = "UNVERIFIED"


class SealProvider(Protocol):
    def sign(self, payload: bytes) -> bytes:
        ...

    def seal(self, payload: bytes) -> HardwareSealResult:
        ...


class AttestationProvider(Protocol):
    def attest(self) -> AttestationEvidence:
        ...


class SealVerifier(Protocol):
    def verify(
        self,
        payload: bytes,
        record: HardwareSealResult,
        *,
        previous_record: HardwareSealResult | None = None,
    ) -> VerificationResult:
        ...


class PublicKeyResolver(Protocol):
    def resolve(self, key: KeyReference) -> bytes | None:
        ...


class SignatureVerifier(Protocol):
    def verify(
        self,
        payload: bytes,
        signature: bytes,
        public_key: bytes,
        algorithm: str,
    ) -> bool:
        ...


class AttestationVerifier(Protocol):
    def verify(
        self,
        payload: bytes,
        record: HardwareSealResult,
        evidence: AttestationEvidence,
    ) -> bool:
        ...


class VersionedSealVerifier:
    """Independent verifier with explicit key and attestation dependencies."""

    def __init__(
        self,
        *,
        keys: PublicKeyResolver,
        signatures: SignatureVerifier,
        attestations: AttestationVerifier | None = None,
        supported_versions: Sequence[int] = (CHAIN_RECORD_VERSION,),
        supported_digests: Sequence[DigestAlgorithm] = tuple(DigestAlgorithm),
    ) -> None:
        self._keys = keys
        self._signatures = signatures
        self._attestations = attestations
        self._supported_versions = frozenset(supported_versions)
        self._supported_digests = frozenset(supported_digests)

    def verify(
        self,
        payload: bytes,
        record: HardwareSealResult,
        *,
        previous_record: HardwareSealResult | None = None,
    ) -> VerificationResult:
        if record.version not in self._supported_versions:
            return VerificationResult(False, None, SealFailure.RECORD_VERSION_UNSUPPORTED)

        if record.payload_digest.algorithm not in self._supported_digests:
            return VerificationResult(False, None, SealFailure.UNSUPPORTED_DIGEST)

        if not record.payload_digest.matches(payload):
            return VerificationResult(False, None, SealFailure.DIGEST_MISMATCH)

        public_key = self._keys.resolve(record.key)
        if public_key is None:
            return VerificationResult(False, None, SealFailure.UNKNOWN_KEY)

        if not self._signatures.verify(
            payload,
            record.signature,
            public_key,
            record.signature_algorithm,
        ):
            return VerificationResult(False, None, SealFailure.SIGNATURE_INVALID)

        if previous_record is not None:
            if record.previous_seal != previous_record.record_hash:
                return VerificationResult(False, None, SealFailure.CHAIN_LINK_INVALID)
        elif record.previous_seal is not None:
            return VerificationResult(False, None, SealFailure.CHAIN_LINK_INVALID)

        if record.strength is SealStrength.HARDWARE_ATTESTED:
            if record.attestation is None:
                return VerificationResult(False, None, SealFailure.MISSING_ATTESTATION)
            if self._attestations is None or not self._attestations.verify(
                payload, record, record.attestation
            ):
                return VerificationResult(False, None, SealFailure.INVALID_ATTESTATION)
            return VerificationResult(
                True,
                SealStrength.HARDWARE_ATTESTED,
                evidence_source=record.attestation.source,
            )

        if record.strength is SealStrength.HARDWARE_BACKED:
            if record.attestation is not None:
                # Optional attestation is not silently promoted. Promotion
                # requires the record to claim HARDWARE_ATTESTED and pass it.
                pass
            return VerificationResult(True, SealStrength.HARDWARE_BACKED, evidence_source=record.key.backend)

        return VerificationResult(True, SealStrength.SOFTWARE, evidence_source=record.key.backend)


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed.astimezone(timezone.utc)
