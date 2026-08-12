"""Verification tests for the versioned seal contract.

TEST HARNESS ONLY. These fixtures deliberately do not represent Secure Enclave,
TPM, SGX, TrustZone, PQC, or production attestation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest

from backend.coordination.hardware_seal import (
    AttestationEvidence,
    DigestAlgorithm,
    HardwareSealResult,
    KeyReference,
    PayloadDigest,
    SealFailure,
    SealStrength,
    VersionedSealVerifier,
)


PAYLOAD = b"test payload"
KEY = KeyReference("sha256:test-key", "TEST_FIXTURE")


class TestKeys:
    def resolve(self, key: KeyReference) -> bytes | None:
        return b"test-public-key" if key == KEY else None


class TestSignatures:
    def verify(self, payload, signature, public_key, algorithm) -> bool:
        return (
            payload == PAYLOAD
            and signature == b"test-signature"
            and public_key == b"test-public-key"
            and algorithm == "TEST-SIGNATURE"
        )


class TestAttestation:
    def verify(self, payload, record, evidence) -> bool:
        return payload == PAYLOAD and evidence.evidence == b"attestation"


def seal(
    *,
    strength: SealStrength = SealStrength.SOFTWARE,
    previous_seal: bytes | None = None,
    attestation: AttestationEvidence | None = None,
) -> HardwareSealResult:
    return HardwareSealResult(
        version=1,
        payload_digest=PayloadDigest.compute(PAYLOAD, DigestAlgorithm.SHA3_512),
        signature_algorithm="TEST-SIGNATURE",
        signature=b"test-signature",
        key=KEY,
        strength=strength,
        timestamp=datetime.now(timezone.utc).isoformat(),
        device_reference="TEST_DEVICE",
        previous_seal=previous_seal,
        attestation=attestation,
    )


def verifier(*, attestations: bool = False) -> VersionedSealVerifier:
    return VersionedSealVerifier(
        keys=TestKeys(),
        signatures=TestSignatures(),
        attestations=TestAttestation() if attestations else None,
    )


def test_digest_records_algorithm_and_value() -> None:
    digest = PayloadDigest.compute(PAYLOAD)
    assert digest.algorithm is DigestAlgorithm.SHA3_512
    assert digest.matches(PAYLOAD)
    assert digest.to_dict()["algorithm"] == "sha3-512"


def test_software_seal_verifies_as_software_only() -> None:
    result = verifier().verify(PAYLOAD, seal())
    assert result.valid is True
    assert result.strength_verified is SealStrength.SOFTWARE
    assert result.evidence_source == "TEST_FIXTURE"


def test_unknown_key_is_rejected() -> None:
    record = seal()
    unknown = HardwareSealResult(
        version=record.version,
        payload_digest=record.payload_digest,
        signature_algorithm=record.signature_algorithm,
        signature=record.signature,
        key=KeyReference("sha256:unknown", "TEST_FIXTURE"),
        strength=record.strength,
        timestamp=record.timestamp,
        device_reference=record.device_reference,
    )
    result = verifier().verify(PAYLOAD, unknown)
    assert result.failure is SealFailure.UNKNOWN_KEY


def test_digest_mismatch_is_rejected() -> None:
    result = verifier().verify(b"different payload", seal())
    assert result.failure is SealFailure.DIGEST_MISMATCH


def test_attested_claim_requires_attestation() -> None:
    result = verifier(attestations=True).verify(
        PAYLOAD,
        seal(strength=SealStrength.HARDWARE_ATTESTED),
    )
    assert result.valid is False
    assert result.failure is SealFailure.MISSING_ATTESTATION


def test_attested_claim_requires_independent_verification() -> None:
    evidence = AttestationEvidence(
        provider="TEST_ATTESTER",
        evidence=b"attestation",
        verified=True,
        source="TEST_FIXTURE",
    )
    result = verifier(attestations=True).verify(
        PAYLOAD,
        seal(strength=SealStrength.HARDWARE_ATTESTED, attestation=evidence),
    )
    assert result.valid is True
    assert result.strength_verified is SealStrength.HARDWARE_ATTESTED
    assert result.evidence_source == "TEST_FIXTURE"


def test_chain_link_must_match_previous_record() -> None:
    previous = seal()
    current = seal(previous_seal=hashlib.sha256(b"wrong").digest())
    result = verifier().verify(PAYLOAD, current, previous_record=previous)
    assert result.failure is SealFailure.CHAIN_LINK_INVALID


def test_record_serialization_exposes_version_key_and_strength() -> None:
    record = seal()
    serialized = record.to_dict()
    assert serialized["version"] == 1
    assert serialized["key"]["key_id"] == "sha256:test-key"
    assert serialized["strength"] == "software"


def test_invalid_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="ISO-8601"):
        HardwareSealResult(
            version=1,
            payload_digest=PayloadDigest.compute(PAYLOAD),
            signature_algorithm="TEST-SIGNATURE",
            signature=b"signature",
            key=KEY,
            strength=SealStrength.SOFTWARE,
            timestamp="not-a-timestamp",
            device_reference="TEST_DEVICE",
        )
