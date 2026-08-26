# Production Transport Protocol

## Non-negotiable transport

Production application transport is TLS-only:

- HTTPS for HTTP APIs and dashboards.
- WSS for WebSocket channels.
- TLS 1.3 minimum.
- Missing TLS material is a hard startup failure.
- No HTTP or WS fallback is permitted.

## Execution boundary

```text
Owner Authority
  -> Policy / Capability Resolution
  -> Transport Gate
  -> HTTPS / WSS
  -> Execution Adapter
  -> SCAR Evidence
  -> Owner-visible Result
```

Transport security does not grant authority. Identity, capability, lease, and policy checks remain mandatory before privileged execution.

## Failure behavior

A paused, blocked, cancelled, or failed operation remains visible. A triaged operation produces a repair proposal and waits for owner approval before mutation. Denial terminates the proposed repair; approval executes and verifies it.

## Repository invariants

- React frontend paths are forbidden and are never recreated.
- Forbidden provider dependencies and unauthorized Google/Meta destinations are rejected.
- `--fix` and `--dry-run` are mutually exclusive.
- `--fix` is real execution, not simulation.
- Every mutation requires explicit authorization and an owner-visible event.
