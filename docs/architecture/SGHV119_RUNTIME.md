# SGHV119 Runtime Contract

`SGHV119.html` is the presentation surface for the Studio ecosystem. It must report real runtime state rather than treating declared capabilities as active.

## State vocabulary

Every subsystem reports one of:

- `DECLARED` — described by configuration or documentation.
- `CONFIGURED` — local settings exist.
- `AVAILABLE` — the adapter and required local dependency are present.
- `VERIFIED` — a local health or integrity check passed.
- `ACTIVE` — the subsystem is currently running and authorized.
- `UNAVAILABLE` — the dependency is missing or not reachable.
- `DENY` — policy prevents the requested operation.
- `REQUIRE_APPROVAL` — owner approval is required.

## Transport

The dashboard uses one transport boundary. Local/offline mode permits loopback only. HTTPS/WSS is reported only when configured; certificate files existing in the repository do not prove that TLS is active.

The browser adapter is `frontend/runtime/transport.js`. It owns endpoint construction and rejects external URLs in local/offline mode.

## Repository integration

`integration/repository-registry.json` is declarative metadata. Listing a repository does not authorize it, start it, clone it, or expose its private state. Future repositories can be added by one manifest entry, an optional adapter, and contract tests.

## SGHV119 cleanup sequence

1. Keep the existing visual dashboard and role/panel content.
2. Replace duplicate bridge managers with the shared transport adapter.
3. Remove fake connected indicators and infinite retry loops.
4. Make local/offline mode allow approved loopback services.
5. Route protected actions through Gate and Risk Engine adapters.
6. Display truthful capability state.
7. Add HTTPS/WSS only through verified local TLS configuration.
8. Run local CI before enabling additional panels.

No provider is universally prohibited by this contract. Provider selection remains deployment-owner policy and requires explicit authorization.
