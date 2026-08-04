# Local contract boundary

This package keeps the existing repositories separate and adds only typed metadata
between the authority, router, enclave, runtime, and evidence layers.

```text
request
  -> TaskEnvelope
  -> Gate authorization
  -> RouteDecision (Genesis)
  -> DevAssist420 or Sovereignty Runtime
  -> ExecutionReceipt
  -> SCAR/REPMHL binding
```

## Ownership

- `Sovereignty-AI-Gate` remains the authority source.
- Genesis routing is represented by `RouteDecision`; it does not grant authority.
- `DevAssist420` remains the local operator/enclave boundary.
- `Sovereignty-AI-Studio` remains the application surface.
- `ExecutionReceipt` contains metadata and hashes, not private payloads.
- `make_scar_event` creates public-safe binding metadata for the existing local ledgers.

## Modes

The contracts use the existing vocabulary:

- `offline` / Ghost: no network access and no cloud fallback.
- `hybrid`: explicitly approved transport only.
- `online` / Cloud: explicit owner-approved online route.

Mode selection is independent from self-hosted runner selection.

## Fail-closed rules

Invalid modes, decisions, missing identifiers, and offline receipts that report
network access are rejected. These contracts do not execute commands, call
providers, persist credentials, or replace Gate authorization.
