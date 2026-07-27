# Patch: Add event_class + route_trace to SCAREvent (aligns with frozen v1.0 contract + hardened x-sovereignty)

# === In SCAREvent dataclass (add after actor or capability_id) ===

from enum import StrEnum

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

    # NEW FIELDS (frozen contract alignment)
    event_class: EventClass
    route_trace: dict | None = None          # Structured route decision trace (for routing/ai_request)
    classification_level: int = 0            # 0-4 visibility level

    previous_event_hash: str
    signature: str
    event_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        # Ensure event_class is always present and valid
        if not isinstance(self.event_class, EventClass):
            object.__setattr__(self, "event_class", EventClass(self.event_class))

    def signing_document(self) -> dict[str, Any]:
        doc = {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "identity_id": self.identity_id,
            "actor": self.actor.value,
            "capability_id": self.capability_id,
            "memory_hash": self.memory_hash,
            "event_class": self.event_class.value,           # NEW
            "previous_event_hash": self.previous_event_hash,
            "metadata": _thaw(self.metadata),
        }
        if self.route_trace is not None:
            doc["route_trace"] = self.route_trace
        if self.classification_level != 0:
            doc["classification_level"] = self.classification_level
        return doc


# === Update append_event signature and body ===

def append_event(
    self,
    event_type: str,
    *,
    actor: SCARActor | str,
    event_class: EventClass | str,
    capability_id: str | None = None,
    memory_hash: str | None = None,
    route_trace: dict | None = None,
    classification_level: int = 0,
    metadata: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> SCAREvent:
    if not event_type:
        raise ValueError("SCAR event_type must not be empty")

    normalized_actor = SCARActor(actor)
    normalized_event_class = EventClass(event_class)

    if normalized_actor == SCARActor.PROVIDER and capability_id is None:
        raise SCARLedgerError("Provider events require capability provenance")

    sequence = len(self._events)
    previous_event_hash = (
        self._events[-1].event_hash if self._events else GENESIS_EVENT_HASH
    )

    signing_document = {
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
        signing_document["route_trace"] = route_trace
    if classification_level != 0:
        signing_document["classification_level"] = classification_level

    signature = self._root_of_trust.sign(
        canonical_bytes(signing_document)
    ).signature

    event_hash = _hash_event(signing_document, signature)

    event = SCAREvent(
        sequence=sequence,
        event_id=signing_document["event_id"],
        event_type=signing_document["event_type"],
        timestamp=signing_document["timestamp"],
        identity_id=signing_document["identity_id"],
        actor=normalized_actor,
        capability_id=signing_document["capability_id"],
        memory_hash=signing_document["memory_hash"],
        event_class=normalized_event_class,
        route_trace=route_trace,
        classification_level=classification_level,
        previous_event_hash=signing_document["previous_event_hash"],
        metadata=signing_document["metadata"],
        signature=signature,
        event_hash=event_hash,
    )
    self._events.append(event)
    return event


# === Example usage for routing events ===

# In SovereignAuthority or routing skill:
ledger.append_event(
    "ROUTE_DECISION",
    actor=SCARActor.DEVICE,
    event_class=EventClass.ROUTING,
    capability_id=decision.capability_id,
    route_trace={
        "trace_id": str(uuid4()),
        "modality": "voice",
        "routing_score": 0.91,
        "test_station_score": 0.88,
        "selected_provider": "xai-sovereign",
        "nist_800_53r_controls": ["AC-2", "AU-9", "SC-8"],
        "fallback_used": False
    },
    classification_level=1,
    metadata={"reason": "voice routing with test station validation"}
)
