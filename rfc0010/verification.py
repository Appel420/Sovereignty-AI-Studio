"""Binding verification for RFC-0010."""

from __future__ import annotations

from typing import Protocol

from rfc0009 import ValidationError


class HasDigest(Protocol):
    """The identity data required by the verification boundary."""

    digest: str


def verify_binding_identity(identity: HasDigest, expected_digest: str) -> None:
    """Verify a declared digest before an artifact can be emitted."""
    if not expected_digest or identity.digest != expected_digest:
        raise ValidationError("binding verification failed")
