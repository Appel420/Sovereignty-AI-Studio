# CanonicalStateLoader

## Purpose

Load and verify canonical device-local runtime state before identity, authority, policy, vault, participant, provider, or network services start.

## Inputs

- local state source
- expected schema version
- trust anchors
- current time
- integrity metadata

## Outputs

- verified canonical state
- deterministic status: `VALID`, `MISSING`, `INVALID`, `STALE`, or `UNVERIFIABLE`
- failure reason
- state fingerprint

## Failure behavior

Any non-`VALID` result fails closed. The loader must deny startup capabilities and emit a local threat event through `SCARLedger` when the ledger is available.

## Required state

Root Authority, identity registry, policy configuration, vault metadata, trust anchors, cryptographic key references, participant registry, cache metadata, and schema/integrity metadata.

## Audit requirements

Record state status, schema version, fingerprint, timestamp, and reason. Do not record secrets or raw state payloads.
