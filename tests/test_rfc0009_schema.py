from dataclasses import FrozenInstanceError

import pytest

from rfc0009 import Schema, SchemaLoader, ValidationError, validate_schema_identity


def test_schema_identity_required_before_vector_loading():
    schema = Schema.from_source("1", {"type": "object"})
    loader = SchemaLoader(schema)

    with pytest.raises(ValidationError, match="schema version required"):
        loader.load_vectors(
            [{"input": "value"}],
            declared_version="",
            declared_snapshot_hash=schema.snapshot_hash,
        )


def test_schema_version_required():
    with pytest.raises(ValidationError, match="schema version required"):
        Schema.from_source("", {"type": "object"})


def test_schema_snapshot_hash_required():
    schema = Schema.from_source("1", {"type": "object"})

    with pytest.raises(ValidationError, match="schema snapshot hash required"):
        validate_schema_identity(schema, "1", "")


def test_unsupported_schema_version_rejected():
    schema = Schema.from_source("1", {"type": "object"})

    with pytest.raises(ValidationError, match="unsupported schema version"):
        validate_schema_identity(schema, "2", schema.snapshot_hash)


def test_schema_snapshot_mismatch_rejected():
    schema = Schema.from_source("1", {"type": "object"})

    with pytest.raises(ValidationError, match="schema snapshot mismatch"):
        validate_schema_identity(schema, "1", "different")


def test_invalid_schema_rejected():
    with pytest.raises(ValidationError, match="invalid schema"):
        Schema.from_source("1", {"value": {1, 2}})


def test_schema_mutation_after_freeze_rejected():
    schema = Schema.from_source("1", {"properties": {"name": {"type": "string"}}})

    with pytest.raises(TypeError):
        schema.raw["properties"]["name"]["type"] = "number"
    with pytest.raises(FrozenInstanceError):
        schema.version = "2"


def test_schema_hash_changes_when_schema_changes():
    first = Schema.from_source("1", {"type": "object"})
    second = Schema.from_source("1", {"type": "array"})

    assert first.snapshot_hash != second.snapshot_hash


def test_identical_schema_snapshots_produce_identical_identity():
    first = Schema.from_source("1", {"type": "object", "properties": {"name": {}}})
    second = Schema.from_source("1", {"properties": {"name": {}}, "type": "object"})

    assert first.snapshot_hash == second.snapshot_hash
