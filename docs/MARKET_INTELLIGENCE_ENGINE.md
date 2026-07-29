# Local-first Market Intelligence Engine

The Market Intelligence Engine handles public model metadata separately from
private device state. It performs no network calls itself. Local adapters may be
injected by the device runtime only after `FeedPolicy` allows a refresh.

## Boundary

```text
Owner policy + explicit consent
            |
            v
Public-feed adapter (injected)
            |
            v
Canonical public records
            |
            v
Local SQLite cache
            |
            +--> ticker
            +--> dashboard
            +--> search
            +--> history
```

The engine never accepts prompts, documents, vault data, memory payloads,
credentials, telemetry, or user identifiers as market records.

## Modes

- `OFFLINE`: adapters are not called; cached records remain readable.
- `GHOST`: use `OFFLINE` policy unless the owner explicitly enables a public feed.
- `HYBRID`: approved public metadata can refresh into the local cache.
- `ONLINE`: still requires an allowed source and explicit consent.

## Empty-state contract

`build_empty_state()` returns an inline, non-blocking state. It must not be
used as a fullscreen overlay and must not remove navigation, filters, tables,
search, or controls.

Example response:

```json
{
  "title": "No feed connected",
  "message": "The dashboard remains available in local mode.",
  "actions": ["Import Local", "Connect Feed"],
  "blocking": false
}
```

## Local validation

```bash
PYTHONPATH=.:./backend pytest -q tests/test_market_intelligence.py
```
