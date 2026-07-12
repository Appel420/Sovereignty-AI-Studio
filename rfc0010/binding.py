"""Ordered RFC-0010 artifact binding pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from . import canonical
from .verification import verify_binding_identity


@dataclass(frozen=True)
class BindingIdentity:
    """Identity derived exclusively from a schema-valid payload."""

    digest: str


@dataclass(frozen=True)
class Artifact:
    """An emitted result bound to a verified payload identity."""

    binding: BindingIdentity
    payload: Mapping[str, Any]


def build_binding_identity(payload: Mapping[str, Any]) -> BindingIdentity:
    """Validate before canonical hashing; no invalid payload gains an identity."""
    canonical.validate_payload_schema(payload)
    return BindingIdentity(digest=canonical.canonical_hash(payload))


def emit_artifact(identity: BindingIdentity, payload: Mapping[str, Any]) -> Artifact:
    """Emit an immutable artifact only after its binding has been verified."""
    return Artifact(binding=identity, payload=MappingProxyType(dict(payload)))


def build_artifact(
    payload: Mapping[str, Any],
    *,
    expected_digest: str,
) -> Artifact:
    """Run the complete schema-to-emission authority sequence."""
    identity = build_binding_identity(payload)
    verify_binding_identity(identity, expected_digest)
    return emit_artifact(identity, payload)
