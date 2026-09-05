"""Fail-closed verification of owner-authorized merge events.

The module deliberately does not depend on a particular post-quantum provider. The
caller supplies a local verifier for the enrolled key and declared signature scheme.
"""
from __future__ import annotations

import base64
import hashlib
import json
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

DOMAIN = "SCAR/MERGE_AUTHORIZATION/v1"
REQUIRED_FIELDS = (
    "event",
    "event_version",
    "proposal_sha",
    "source_sha",
    "target_branch",
    "approved_by",
    "approval_method",
    "signer_key_id",
    "signature_scheme",
    "signature",
    "timestamp",
)


class AuthorizationError(ValueError):
    """Raised when an authorization record is malformed or invalid."""


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {_normalize(str(key)): _normalize(item) for key, item in value.items()}
    return value


def canonical_json(value: Mapping[str, Any]) -> bytes:
    """Return deterministic UTF-8 JSON bytes for protocol-significant objects."""
    return json.dumps(
        _normalize(dict(value)),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_canonical(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def canonical_authorization_message(authorization: Mapping[str, Any]) -> bytes:
    """Build the domain-separated message covered by the owner signature."""
    fields = (
        DOMAIN,
        str(authorization["proposal_sha"]),
        str(authorization["source_sha"]),
        str(authorization["target_branch"]),
        str(authorization["approved_by"]),
        str(authorization["approval_method"]),
        str(authorization["signer_key_id"]),
        str(authorization["signature_scheme"]),
        str(authorization["timestamp"]),
    )
    return "\n".join(fields).encode("utf-8")


def _validate_timestamp(value: Any) -> None:
    if not isinstance(value, str):
        raise AuthorizationError("timestamp must be an RFC3339 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorizationError("timestamp must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AuthorizationError("timestamp must include a timezone")
    if parsed.astimezone(timezone.utc).isoformat() != parsed.astimezone(timezone.utc).isoformat():
        raise AuthorizationError("invalid timestamp")


def _signature_bytes(value: Any) -> bytes:
    if not isinstance(value, str) or not value.startswith("base64url:"):
        raise AuthorizationError("signature must use the base64url: prefix")
    encoded = value.removeprefix("base64url:")
    try:
        return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise AuthorizationError("signature is not valid base64url") from exc


def verify_authorization(
    proposal: Mapping[str, Any],
    authorization: Mapping[str, Any],
    owner_keys: Mapping[str, bytes],
    verify_signature: Callable[[str, bytes, bytes, bytes], bool],
    *,
    producing_agent_id: str | None = None,
) -> bool:
    """Verify an owner authorization against a proposal and anchored key registry.

    ``verify_signature`` receives ``scheme``, public key, canonical message, and raw
    signature bytes. Keeping provider-specific crypto outside this module makes the
    contract testable offline and allows a local ML-DSA/Falcon implementation to be
    injected without network access.
    """
    try:
        if any(field not in authorization for field in REQUIRED_FIELDS):
            return False
        if authorization["event"] != "merge_authorized" or authorization["event_version"] != 1:
            return False
        if authorization["approved_by"] != "human-owner":
            return False
        if producing_agent_id is not None and authorization["approved_by"] == producing_agent_id:
            return False
        if authorization["proposal_sha"] != sha256_canonical(proposal):
            return False
        if authorization["source_sha"] != proposal.get("source_sha"):
            return False
        if authorization["target_branch"] != proposal.get("target_branch"):
            return False
        _validate_timestamp(authorization["timestamp"])
        key_id = authorization["signer_key_id"]
        public_key = owner_keys.get(key_id)
        if not isinstance(public_key, bytes):
            return False
        signature = _signature_bytes(authorization["signature"])
        message = canonical_authorization_message(authorization)
        return bool(
            verify_signature(
                str(authorization["signature_scheme"]), public_key, message, signature
            )
        )
    except (AuthorizationError, KeyError, TypeError, ValueError):
        return False


def validate_authorization_history(
    authorizations: Iterable[Mapping[str, Any]],
) -> bool:
    """Reject duplicate/conflicting authorizations for the same proposal."""
    seen: dict[tuple[Any, Any], Mapping[str, Any]] = {}
    for authorization in authorizations:
        key = (authorization.get("proposal_sha"), authorization.get("source_sha"))
        if key in seen:
            previous = seen[key]
            if dict(previous) != dict(authorization):
                return False
            return False
        seen[key] = authorization
    return True
