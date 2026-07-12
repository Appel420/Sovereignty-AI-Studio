# Repository Inventory and Ownership

## Canonical Studio runtime

The repository root is the only supported Sovereignty AI Studio runtime.
Its supported entry points are:

- `SGHv119.html` — KODER dashboard.
- `START_SERVER.sh` — local dashboard, Python bridge, and Node bridge launcher.
- `bridge.py` — Python local bridge.
- `node-bridge/` — Node HTTP/API bridge.
- `backend/` and `gateway/` — self-hosted service stack.

First-party Studio code also lives in `agents/`, `ai_agents/`, `ai_core/`,
`frontend/`, `ios/`, `rust/`, `scripts/`, `src/`, `tests/`, and `docs/`.
Only root configuration, launchers, and CI define the supported runtime.

## External vendor projects

`external/` contains whole projects preserved with their upstream metadata and
licenses. They are not imported by the root launchers, Docker Compose file, or
test suite. Root linting, type checking, and test discovery must exclude this
directory.

| Path | Classification | Ownership |
| --- | --- | --- |
| `external/SuperGrok-Heavy-4-2-Skeleton/` | Managed vendor workspace | Synced only by the SuperGrok sync workflow |
| `external/python-keycloak/` | Vendored third-party distribution | Maintained and tested by its upstream project |

The SuperGrok vendor contains historical Studio deployments, Lightning, and
Vocalinux. Those nested projects remain vendor content rather than alternate
Studio runtimes.

## Archives and binary artifacts

Historical snapshots and binary artifacts belong in `archives/` or
`resources/assets/`, never in an active application directory. They require a
provenance note and must not become a runtime dependency. A candidate can be
removed only after confirming it is absent from root imports, launch scripts,
Docker and CI definitions, documentation, and tests.

## Contribution rule

Do not add a complete project, dependency source tree, generated build output,
or duplicate launcher to the repository root. Add first-party code to its
canonical component; add third-party source under `external/`; and archive
immutable historical material outside active runtime paths.
