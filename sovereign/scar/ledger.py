"""Append-only SCAR evidence ledger.

Canonical runtime implementation for the frozen SCAR v1 contract plus
``event_class``, ``route_trace`` and ``classification_level``.

The ledger deliberately owns no network transport and does not expose raw
private payloads. A caller supplies the project's root-of-trust signer.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping, Protocol
from uuid import uuid4


GENESIS_EVENT_HASH = "0" * 64


class SCARLedgerError(RuntimeError):
    """Raised when an event cannot be safely appended."""


class SCARActor(StrEnum):
    USER = "user"
    DEVICE = "device"
    PROVIDER = "provider"
    SYSTEM = "system"


class EventClass(StrEnum):
    SENSOR = "sensor"
    MEMORY = "memory"
    AI_REQUEST = "ai_request"
    MODEL_REGISTRY = "model_registry"
    ROUTING = "routing"
    POLICY = "policy"
    CONSENT = "consent"
    SYSTEM = "system"
    SECURITY = "security"
    AUDIT = "audit"


class RootOfTrust(Protocol):
    def sign(self, payload: bytes) -> Any: ...


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _freeze(v) for k, v in value.items()}
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    if isinstance(value, dict):
        return {k: _thaw(v) for k, v in value.items()}
    return value


def canonical_bytes(document: Mapping[str, Any]) -> bytes:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _hash_event(document: Mapping[str, Any], signature: str) -> str:
    payload = canonical_bytes({"document": document, "signature": signature})
    return hashlib.sha256(payload).hexdigest()


def _signature_text(signed: Any) -> str:
    value = getattr(signed, "signature", signed)
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


@dataclass(frozen=True)
class SCAREvent:
    sequence: int
    event_id: str
    event_type: str
    timestamp: str
    identity_id: str
    actor: SCARActor
    capability_id: str | None
    memory_hash: str | None
    event_class: EventClass
    route_trace: Mapping[str, Any] | None = None
    classification_level: int = 0
    previous_event_hash: str = GENESIS_EVENT_HASH
    signature: str = ""
    event_hash: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze(dict(self.metadata)))
        if self.route_trace is not None:
            object.__setattr__(self, "route_trace", _freeze(dict(self.route_trace)))
        object.__setattr__(self, "actor", SCARActor(self.actor))
        object.__setattr__(self, "event_class", EventClass(self.event_class))
        if not 0 <= self.classification_level <= 4:
            raise ValueError("classification_level must be between 0 and 4")

    def signing_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "identity_id": self.identity_id,
            "actor": self.actor.value,
            "capability_id": self.capability_id,
            "memory_hash": self.memory_hash,
            "event_class": self.event_class.value,
            "previous_event_hash": self.previous_event_hash,
            "metadata": _thaw(self.metadata),
        }
        if self.route_trace is not None:
            document["route_trace"] = _thaw(self.route_trace)
        if self.classification_level != 0:
            document["classification_level"] = self.classification_level
        return document


class SCARLedger:
    """Append-only, hash-chained SCAR ledger."""

    def __init__(self, identity_id: str, root_of_trust: RootOfTrust) -> None:
        if not identity_id:
            raise ValueError("identity_id must not be empty")
        self.identity_id = identity_id
        self._root_of_trust = root_of_trust
        self._events: list[SCAREvent] = []

    @property
    def events(self) -> tuple[SCAREvent, ...]:
        return tuple(self._events)

    def append_event(
        self,
        event_type: str,
        *,
        actor: SCARActor | str,
        event_class: EventClass | str,
        capability_id: str | None = None,
        memory_hash: str | None = None,
        route_trace: dict[str, Any] | None = None,
        classification_level: int = 0,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> SCAREvent:
        if not event_type:
            raise ValueError("SCAR event_type must not be empty")
        if not 0 <= classification_level <= 4:
            raise ValueError("classification_level must be between 0 and 4")

        normalized_actor = SCARActor(actor)
        normalized_event_class = EventClass(event_class)
        if normalized_actor == SCARActor.PROVIDER and capability_id is None:
            raise SCARLedgerError("Provider events require capability provenance")

        sequence = len(self._events)
        previous_event_hash = self._events[-1].event_hash if self._events else GENESIS_EVENT_HASH
        signing_document: dict[str, Any] = {
            "sequence": sequence,
            "event_id": str(uuid4()),
            "event_type": event_type,
            "timestamp": timestamp or _utc_timestamp(),
            "identity_id": self.identity_id,
            "actor": normalized_actor.value,
            "capability_id": capability_id,
            "memory_hash": memory_hash,
            "event_class": normalized_event_class.value,
            "previous_event_hash": previous_event_hash,
            "metadata": deepcopy(metadata or {}),
        }
        if route_trace is not None:
            signing_document["route_trace"] = deepcopy(route_trace)
        if classification_level != 0:
            signing_document["classification_level"] = classification_level

        signature = _signature_text(self._root_of_trust.sign(canonical_bytes(signing_document)))
        event_hash = _hash_event(signing_document, signature)
        event = SCAREvent(
            sequence=sequence,
            event_id=signing_document["event_id"],
            event_type=event_type,
            timestamp=signing_document["timestamp"],
            identity_id=self.identity_id,
            actor=normalized_actor,
            capability_id=capability_id,
            memory_hash=memory_hash,
            event_class=normalized_event_class,
            route_trace=route_trace,
            classification_level=classification_level,
            previous_event_hash=previous_event_hash,
            signature=signature,
            event_hash=event_hash,
            metadata=signing_document["metadata"],
        )
        self._events.append(event)
        return event

    def verify_chain(self) -> bool:
        previous = GENESIS_EVENT_HASH
        for index, event in enumerate(self._events):
            document = event.signing_document()
            if event.sequence != index or event.previous_event_hash != previous:
                return False
            if _hash_event(document, event.signature) != event.event_hash:
                return False
            previous = event.event_hash
        return True
