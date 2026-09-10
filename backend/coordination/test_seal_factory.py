from __future__ import annotations

from backend.coordination.hardware_seal import KeyReference, SealFailure, SealStrength, SignatureKind
from backend.coordination.seal_factory import HardwareSealError, HardwareUnavailable, seal_in_hardware


class FakeHardware:
    backend = "test-tpm"
    algorithm = "TEST-SIGNATURE"
    key = KeyReference("test-key", "test-tpm")
    device_reference = "TEST-DEVICE"

    def sign(self, payload: bytes) -> bytes:
        return b"signature:" + payload


class UnavailableHardware(FakeHardware):
    def sign(self, payload: bytes) -> bytes:
        raise HardwareUnavailable


class FailingHardware(FakeHardware):
    def sign(self, payload: bytes) -> bytes:
        raise HardwareSealError


class EmptyHardware(FakeHardware):
    def sign(self, payload: bytes) -> bytes:
        return b""


def test_payload_hash_is_backend_independent() -> None:
    payload = b"same payload"
    hardware = seal_in_hardware(payload, backend=FakeHardware())
    software = seal_in_hardware(payload)
    assert hardware.result.payload_digest == software.result.payload_digest


def test_hardware_result_contains_signature_identity() -> None:
    outcome = seal_in_hardware(b"payload", backend=FakeHardware())
    assert outcome.fallback is False
    assert outcome.result.strength is SealStrength.HARDWARE_BACKED
    assert outcome.result.signature_kind is SignatureKind.SIGNATURE
    assert outcome.result.signature == b"signature:payload"
    assert outcome.result.key.key_id == "test-key"
    assert outcome.result.signature_algorithm == "TEST-SIGNATURE"


def test_missing_backend_is_explicit_software_digest() -> None:
    outcome = seal_in_hardware(b"payload")
    assert outcome.fallback is True
    assert outcome.result.strength is SealStrength.SOFTWARE
    assert outcome.result.signature_kind is SignatureKind.DIGEST
    assert outcome.result.key.backend == "software"
    assert outcome.result.signature_algorithm == "SHA3-512-DIGEST"


def test_hardware_unavailability_falls_back_explicitly() -> None:
    outcome = seal_in_hardware(b"payload", backend=UnavailableHardware())
    assert outcome.fallback is True
    assert outcome.result.signature_kind is SignatureKind.DIGEST


def test_hardware_failure_falls_back_explicitly() -> None:
    outcome = seal_in_hardware(b"payload", backend=FailingHardware())
    assert outcome.fallback is True
    assert outcome.result.strength is SealStrength.SOFTWARE


def test_empty_signature_falls_back_explicitly() -> None:
    outcome = seal_in_hardware(b"payload", backend=EmptyHardware())
    assert outcome.fallback is True
    assert outcome.result.signature_kind is SignatureKind.DIGEST


def test_previous_seal_is_preserved_across_fallback() -> None:
    previous = b"previous-record-hash"
    outcome = seal_in_hardware(b"payload", previous_seal=previous)
    assert outcome.result.previous_seal == previous


def test_non_bytes_payload_is_rejected() -> None:
    try:
        seal_in_hardware("payload")  # type: ignore[arg-type]
    except TypeError:
        pass
    else:
        raise AssertionError("non-bytes payload must be rejected")


def test_software_digest_can_be_verified_without_key_possession() -> None:
    outcome = seal_in_hardware(b"payload")

    class Keys:
        def resolve(self, key):
            return None

    class Signatures:
        def verify(self, *args):
            raise AssertionError("digest fallback must not invoke signature verification")

    from backend.coordination.hardware_seal import VersionedSealVerifier

    result = VersionedSealVerifier(keys=Keys(), signatures=Signatures()).verify(
        b"payload", outcome.result
    )
    assert result.valid is True
    assert result.strength_verified is SealStrength.SOFTWARE


def test_software_digest_is_rejected_when_key_possession_is_required() -> None:
    outcome = seal_in_hardware(b"payload")

    class Keys:
        def resolve(self, key):
            return None

    class Signatures:
        def verify(self, *args):
            return False

    from backend.coordination.hardware_seal import VersionedSealVerifier

    result = VersionedSealVerifier(keys=Keys(), signatures=Signatures()).verify(
        b"payload", outcome.result, require_key_possession=True
    )
    assert result.valid is False
    assert result.failure is SealFailure.SIGNATURE_KIND_MISMATCH
