"""Schema authority boundaries for RFC-0009."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha3_512
import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping
import unicodedata

from .core import ValidationError


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", key): _json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return value


def canonical_schema_bytes(raw: Mapping[str, Any]) -> bytes:
    """Return deterministic RFC-0003-style JSON bytes for a schema mapping."""
    if not isinstance(raw, Mapping):
        raise ValidationError("invalid schema")
    try:
        return json.dumps(
            _json_value(raw),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValidationError("invalid schema") from exc


def _schema_snapshot_hash(raw: Mapping[str, Any]) -> str:
    return sha3_512(canonical_schema_bytes(raw)).hexdigest()


@dataclass(frozen=True)
class Schema:
    """An immutable schema whose identity is bound to canonical source bytes."""

    version: str
    snapshot_hash: str
    raw: Mapping[str, Any]
    _canonical_bytes: bytes = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        frozen_raw = _freeze(self.raw)
        canonical_bytes = canonical_schema_bytes(frozen_raw)
        expected_hash = sha3_512(canonical_bytes).hexdigest()
        object.__setattr__(self, "raw", frozen_raw)
        object.__setattr__(self, "_canonical_bytes", canonical_bytes)
        self.validate()
        if self.snapshot_hash != expected_hash:
            raise ValidationError("schema snapshot mismatch")

    @classmethod
    def from_source(cls, version: str, raw: Mapping[str, Any]) -> "Schema":
        """Validate, canonicalize, and freeze a schema source."""
        return cls(version=version, snapshot_hash=_schema_snapshot_hash(raw), raw=raw)

    def validate(self) -> None:
        if not isinstance(self.version, str) or not self.version:
            raise ValidationError("schema version required")
        if not isinstance(self.snapshot_hash, str) or not self.snapshot_hash:
            raise ValidationError("schema snapshot hash required")
        canonical_schema_bytes(self.raw)


def validate_schema_identity(
    schema: Schema,
    declared_version: str,
    declared_snapshot_hash: str,
) -> None:
    """Reject declarations that are not bound to a frozen schema snapshot."""
    if not declared_version:
        raise ValidationError("schema version required")
    if schema.version != declared_version:
        raise ValidationError("unsupported schema version")
    if not declared_snapshot_hash:
        raise ValidationError("schema snapshot hash required")
    if schema.snapshot_hash != declared_snapshot_hash:
        raise ValidationError("schema snapshot mismatch")


@dataclass(frozen=True)
class SchemaLoader:
    """Loads vectors only after their declared schema identity is validated."""

    schema: Schema

    def load_vectors(
        self,
        vectors: Iterable[Any],
        *,
        declared_version: str,
        declared_snapshot_hash: str,
    ) -> tuple[Any, ...]:
        validate_schema_identity(
            self.schema,
            declared_version,
            declared_snapshot_hash,
        )
        return tuple(vectors)
