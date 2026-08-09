"""Tests that production claims require explicit provenance."""
from __future__ import annotations

import pytest

from backend.coordination.hardware_seal import (
    AttestationEvidence,
    DigestAlgorithm,
    HardwareSealResult,
    KeyReference,
    PayloadDigest,
    SealStrength,
    VersionedSealVerifier,
)


def test_hardware_attested_without_real_attestation_is_rejected() -> None:
    payload = b"production claim test"
    record = HardwareSealResult(
        version=1,
        payload_digest=PayloadDigest.compute(payload, DigestAlgorithm.SHA3_512),
        signature_algorithm="UNAVAILABLE",
        signature=b"not-a-production-signature",
        key=KeyReference("sha256:test", "TEST_FIXTURE"),
        strength=SealStrength.HARDWARE_ATTESTED,
        timestamp="2026-08-06T00:00:00+00:00",
        device_reference="TEST_DEVICE",
    )

    class Keys:
        def resolve(self, _key):
            return b"test-key"

    class Signatures:
        def verify(self, *_args):
            return True

    result = VersionedSealVerifier(keys=Keys(), signatures=Signatures()).verify(payload, record)
    assert result.valid is False
    assert result.failure.value == "missing_attestation"


def test_attestation_evidence_does_not_self_authorize() -> None:
    evidence = AttestationEvidence(
        provider="TEST_FIXTURE",
        evidence=b"synthetic",
        verified=True,
        source="TEST_HARNESS",
    )
    assert evidence.verified is True
    assert evidence.source == "TEST_HARNESS"
    # The contract exposes the source; independent verification remains required.
    assert evidence.source != "HARDWARE_ATTESTATION"
