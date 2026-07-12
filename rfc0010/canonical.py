"""Canonical payload representation at the RFC-0010 binding boundary."""

from __future__ import annotations

from hashlib import sha3_512
import json
from typing import Any, Mapping
import unicodedata

from rfc0009 import ValidationError


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValidationError("payload schema invalid")
        return {
            unicodedata.normalize("NFC", key): _canonical_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return value


def validate_payload_schema(payload: Mapping[str, Any]) -> None:
    """Confirm that a payload is structurally eligible for canonicalization."""
    if not isinstance(payload, Mapping) or not payload:
        raise ValidationError("payload schema invalid")
    try:
        json.dumps(_canonical_value(payload), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError("payload schema invalid") from exc


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """Produce RFC-0003-compatible canonical JSON bytes."""
    return json.dumps(
        _canonical_value(payload),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_hash(payload: Mapping[str, Any]) -> str:
    """Derive a digest from a canonical payload representation."""
    return sha3_512(canonical_bytes(payload)).hexdigest()
