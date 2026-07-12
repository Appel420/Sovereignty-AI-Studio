import pytest

from rfc0009 import ValidationError
from rfc0010 import build_artifact, build_binding_identity


def test_schema_validation_precedes_hashing(monkeypatch):
    calls = []

    def schema_check(payload):
        calls.append("schema")

    def hash_check(payload):
        calls.append("hash")
        return "digest"

    monkeypatch.setattr("rfc0010.canonical.validate_payload_schema", schema_check)
    monkeypatch.setattr("rfc0010.canonical.canonical_hash", hash_check)

    build_binding_identity({"kind": "artifact"})

    assert calls == ["schema", "hash"]


def test_invalid_payload_cannot_reach_hashing(monkeypatch):
    def hash_check(payload):
        pytest.fail("invalid payload reached hashing")

    monkeypatch.setattr("rfc0010.canonical.canonical_hash", hash_check)

    with pytest.raises(ValidationError, match="payload schema invalid"):
        build_binding_identity({})


def test_binding_verification_precedes_artifact_emission(monkeypatch):
    def emit(*args, **kwargs):
        pytest.fail("unverified binding emitted an artifact")

    monkeypatch.setattr("rfc0010.binding.emit_artifact", emit)

    with pytest.raises(ValidationError, match="binding verification failed"):
        build_artifact({"kind": "artifact"}, expected_digest="incorrect")


def test_verified_binding_emits_immutable_artifact():
    payload = {"kind": "artifact"}
    identity = build_binding_identity(payload)

    artifact = build_artifact(payload, expected_digest=identity.digest)

    assert artifact.binding == identity
    with pytest.raises(TypeError):
        artifact.payload["kind"] = "other"
