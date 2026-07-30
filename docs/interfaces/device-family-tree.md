# Device-Local Family-Tree Interface

## Purpose

The family-tree registry describes device-local storage identities and the local Router/Council layout. It is a filesystem contract, not proof that any provider, model, or runtime is installed or active.

## Local-only boundary

- The registry is created by `scripts/create-device-family-tree.sh`.
- The default root is `$HOME/Admin/On Device Memory Storage`.
- `SOVEREIGN_STATE_ROOT` may override the root for local testing.
- The initializer performs no network calls and does not contact GitHub or providers.
- Network and external memory are disabled by registry contract.
- The dashboard loads only a same-origin `provider-registry.json` and falls back to embedded metadata when it is unavailable.

## Dashboard fields

Each provider displays:

- **IDENTITY** — registry identifier.
- **ROLE** — declared local role, not an authority grant.
- **LOCAL STORAGE** — filesystem storage identity.
- **MEMORY** — always `DEVICE ONLY`.
- **NETWORK** — always `DISABLED` unless the registry boundary rejects the data.
- **AUTHORIZATION** — defaults to `NOT EVALUATED`; presence in the registry never authorizes access.
- **SCAR HISTORY** — `LOCAL-ONLY / UNAVAILABLE` until an existing local ledger is connected.

## Wake-word boundary

The registry records `hey ara` as a requested wake word, but recognition remains `local_engine_required`, `remote_recognition` is `false`, and status is `not_configured`. The interface must not claim that a local wake-word or TTS engine is installed or active. No background listening is started by the dashboard.

## Evidence and testing

Changes are validated with local shell, JSON, frontend, and Python tests. The local-first SCAR record remains the evidence boundary. Tests must reject cloud URLs, provider calls, remote recognition, and silent authorization.
