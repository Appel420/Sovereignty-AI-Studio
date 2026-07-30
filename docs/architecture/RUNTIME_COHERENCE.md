# Runtime Coherence and Duplicate Cleanup Plan

The Studio currently contains multiple dashboards, bridge launchers, HTTP servers,
security layers, and compatibility wrappers. They are not all equivalent. The
runtime must therefore be **canonical, explicit, and symmetric** instead of
trying to make every historical file active at once.

## Canonical runtime

```text
SGHv119.html
  -> START_SERVER.sh
      -> bridge.py (:9897)
      -> node-bridge/server.js (:9899)
      -> static server (:9898)
  -> frontend/runtime/transport.js
  -> frontend/runtime/hawking-channel.js
  -> frontend/runtime/sg-hawking-integration.js
  -> integration/repository-registry.json
```

The canonical runtime map is stored in `config/runtime-coherence.json`.

## Compatibility and legacy files

Compatibility wrappers may remain for users who already call them, but they are
not additional runtime owners. Legacy or separate runtimes must not be started by
the canonical launcher and must not publish a competing status value.

The validator currently tracks:

- `start-all.sh` as an alias of `START_SERVER.sh`;
- `python3_bridge.py` as an alias of `bridge.py`;
- `sovereignty_full_server.py` as an alias of `bridge.py`;
- alternate servers and dashboards as legacy/separate runtime candidates.

## Status truthfulness

A status is only allowed to say `ACTIVE` after a real local health check. Otherwise
it must say `DECLARED`, `CONFIGURED`, `AVAILABLE`, `VERIFIED`, `UNAVAILABLE`,
`DENY`, or `REQUIRE_APPROVAL`.

No static dashboard label proves that TLS, WSS, mTLS, PQC, a repository, a provider,
or a security service is active.

## Symmetric repository integration

Repositories are participants in the manifest, not hidden runtime dependencies.
Each participant has a role, capabilities, trust boundary, and policy state. A
new repository is added through one manifest entry, an optional adapter, and local
contract tests.

## Cleanup rule

Do not delete large historical files blindly. First classify them as:

1. canonical runtime;
2. compatibility alias;
3. optional adapter;
4. documentation/example;
5. legacy or separate runtime;
6. private local state.

Then either wire the file through the canonical boundary or remove its claim to be
an active runtime. This preserves the visual dashboard while eliminating duplicate
owners and contradictory status paths.

## Local validation

```bash
python3 scripts/validate-runtime-coherence.py
python3 -m pytest -q tests/test_runtime_coherence.py
bash scripts/local-ci.sh
```

These checks are local-only. They do not start services, contact a provider, create
keys, publish artifacts, or use a hosted/cloud runner.
