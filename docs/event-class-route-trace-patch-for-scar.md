# SCAR route-trace patch template

This is an instructional patch for adding `event_class` and `route_trace` to `SCAREvent`. It is intentionally documentation, not an executable module. Apply the snippets to the repository's actual SCAR ledger implementation with the project's existing imports and types.

## Event class

```python
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
```

## Required event fields

```python
@dataclass(frozen=True)
class SCAREvent:
    # Existing fields remain unchanged.
    event_class: EventClass
    route_trace: dict | None = None
    classification_level: int = 0
```

The actual implementation must import `dataclass`, `field`, `Mapping`, `Any`, and all repository-local helpers before using them. Do not copy this template into a runtime module without adapting those dependencies.

## Append contract

`append_event` should normalize `event_class`, preserve the previous event hash, include `route_trace` and `classification_level` in the signed document, and append the resulting event without mutating prior entries.

## Route evidence example

```python
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
        "fallback_used": False,
    },
    classification_level=1,
    metadata={"reason": "voice routing with test station validation"},
)
```

The route trace is evidence metadata. It must not contain credentials, private keys, raw private payloads, or secrets.
