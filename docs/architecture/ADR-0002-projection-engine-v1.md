# ADR-0002: ProjectionEngine v1.0

- **Status:** Accepted
- **Date:** 2026-07-29
- **Scope:** Ecosystem menu, dashboard builder, audit projection, and cache isolation

## Context

The Studio contains a broad ecosystem catalog: direct links, local routes,
role schemas, tools, safety panels, and administrative capabilities. Catalog
membership must not be confused with visibility, authorization, assignment, or
runtime availability. A client-controlled projection parameter must never grant
privilege.

The root `SGHv119.html` dashboard is the canonical frontend surface served by
`START_SERVER.sh`. The canonical Python application package is under
`backend/`; `external/` and historical dashboard HTML files are not runtime
sources for this contract.

## Decision

Introduce a framework-agnostic `ProjectionEngine v1.0` at
`backend/ecosystem/projection_engine.py`.

The declarative manifest contains catalog facts only. It must not store
request-specific `visible` or `enabled` values.

For every authenticated request, the server evaluates:

```text
identity
  -> grants and assignments
  -> policy and projection authority
  -> runtime health
  -> projected DTO
  -> renderer
```

### Projections

| Projection | Visibility | Data mode |
| --- | --- | --- |
| `user` | Assigned and authorized items | Permitted live data; private data redacted |
| `builder` | Authorized items and schema-only items | Synthetic data only |
| `audit` | Complete catalog metadata | Metadata/evidence only; no payloads or secrets |

Projection is derived from the authenticated context. Query parameters may be
used as a requested view, but cannot elevate a user to `builder` or `audit`.

### Enablement

Visibility and execution are separate. An item is enabled only when it is
visible, authorized, runtime healthy, and neither `DENY` nor `UNAVAILABLE`.

### Audit DTO boundary

Audit responses use a dedicated metadata-only DTO. Private payloads,
credentials, tokens, memory content, and user records are not copied into the
DTO and therefore cannot reach the renderer through this contract.

### Cache isolation

Projection cache keys must include:

- identity ID;
- roles and grants;
- assignments;
- policy version;
- manifest version;
- assignment version;
- projection.

A cache entry missing any of those fields is invalid. Projection results are
immutable for the request lifecycle.

## Consequences

- The full role and ecosystem catalog can remain available to authorized audit
  and builder workflows without appearing in normal user projections.
- Builder previews can repair and design dashboards using synthetic data.
- Runtime failures are visible and fail closed instead of being silently
  substituted.
- A future FastAPI route can wrap this engine without moving authorization into
  the browser.

## Rejected alternatives

- Storing `visible` in the manifest: becomes stale authorization state.
- Trusting `?projection=audit`: client-controlled privilege escalation.
- Reusing one global projection cache: cross-identity data leakage.
- Sending raw catalog objects to audit clients: accidental secret/payload leak.
