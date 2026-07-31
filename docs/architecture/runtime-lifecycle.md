# Runtime Lifecycle

## Canonical lifecycle

```text
Power On
  → Hardware Validation
  → Load Canonical Runtime State
  → Verify Integrity and Freshness
  → Verify Identity
  → Verify Root Authority
  → Initialize Policy Engine
  → Open Vault
  → Open SCARLedger
  → Load Participant Registry
  → Load Market Cache
  → Start Dashboard
  → Await Mission
```

No provider, network client, credential consumer, polling loop, WebSocket, or SSE stream initializes before policy success.

## Mission lifecycle

```text
NO ACTIVE MISSION
  → owner-authenticated wake event
ACTIVE MISSION
  → policy-bound action
MISSION COMPLETE
  → NO ACTIVE MISSION
```

Canonical state remains loaded throughout.

## Fail-closed lifecycle

```text
Missing / invalid / stale / unverifiable state
  → local threat event
  → owner alert where possible
  → deny provider, credential, mission, and network capabilities
  → preserve safe local diagnostics
```

## Shutdown and recovery

Shutdown closes mission state first, flushes local evidence, seals the ledger checkpoint, and then releases runtime services. Recovery never silently broadens permissions or changes policy.
