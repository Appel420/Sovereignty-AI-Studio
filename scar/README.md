# SCAR Evidence Boundary

SCAR is an evidence sink, not an authority source.

## Invariants

- Runtime components may emit evidence; they may not rewrite historical events.
- Each accepted event is append-only and must carry provenance sufficient to reconstruct 5W1H: who, what, when, where, why, how.
- Evidence is written by the dedicated SCAR CI/evidence boundary, independently of ordinary lint/test workflows.
- A failed validation remains visible as evidence; it is never converted into success by cancellation, skipping, or UI filtering.
- Local agents may diagnose, propose, and apply authorized fixes inside their assigned scope. They do not grant themselves authority or silently promote protected state.
- Human approval remains required for protected repository promotion and other policy-defined high-risk operations.

## CI separation

Repository CI remains responsible for build/test/lint/OAuth and integration validation. SCAR CI is a separate evidence pipeline that consumes deterministic results and appends an immutable evidence record.

The separation is:

```text
Repository CI / OAuth / Lint / Tests
              |
              v
       deterministic result
              |
              v
         SCAR Evidence CI
              |
              v
       append-only record
              |
              v
        owner-visible state
```

SCAR CI must never be made read-only at the point where evidence is supposed to be appended. Instead, the historical ledger is immutable while the emitter has narrowly scoped append permission.
