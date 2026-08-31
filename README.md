[![.github/workflows/python-ci.yml](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/python-ci.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/python-ci.yml)[![CI](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ci.yml) [![iOS Sovereign Build (local-first)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ios-sovereign-build.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ios-sovereign-build.yml) [![Quart App CI](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/Quart.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/Quart.yml)  [![oauth-api-generator.yaml](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/oauth-api-generator.yaml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/oauth-api-generator.yaml) [![Pylint](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/pylint.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/pylint.yml) [![CI Health Probe](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ci-health-probe.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ci-health-probe.yml)
# Sovereignty AI Studio

@claude @codex @copilot @grok @duckai

This is the main dedicated branch. All changes by Claude Grok/Ara DuckAI GPT/Codex Copilot must be made in their dedicated branch. Do not push directly to main. Create a Pull Request for review.

Sovereignty AI Studio is a self-hosted, offline-first AI control surface and supporting service stack. The primary user interface is the KODER dashboard in [`SGHv119.html`](SGHv119.html); Python and Node services provide local routing, agent orchestration, and optional self-hosted integrations.

## Runtime governance

The canonical runtime modes are **LOCAL**, **HYBRID**, and **ONLINE**. LOCAL is the default and is device-offline/loopback-only. HYBRID and ONLINE require explicit deployment-owner authorization and must not be inferred from legacy names.

Runtime artifacts are classified as **canonical**, **derived**, or **external**. Canonical artifacts define the runtime contract; derived artifacts are generated or secondary representations; external artifacts require explicit authorization before execution or ingestion.

The primary local dashboard/runtime path is **PHPWin** -> Python bridge -> Node bridge. Status endpoints must report `UNAVAILABLE`, `DENY`, or `REQUIRE_APPROVAL` rather than claiming an unavailable capability is active.

## Canonical runtime map

```text
SGHv119.html
  -> START_SERVER.sh
      -> static dashboard :9898
      -> bridge.py         :9897
      -> node-bridge/server.js :9899
  -> frontend/runtime/transport.js
  -> frontend/runtime/hawking-channel.js
  -> frontend/runtime/sg-hawking-integration.js
  -> frontend/runtime/sghv119-bootstrap.js
  -> integration/repository-registry.json
```

`config/runtime-coherence.json` is the source of truth for the dashboard, launcher, bridge paths, ports, aliases, and legacy/separate-runtime classification.

Compatibility launchers remain aliases; they are not additional runtime owners. Historical servers, alternate dashboards, security experiments, and deployment examples must be explicitly classified before they are wired into the canonical path.

## What is included

- **KODER dashboard:** a plain HTML, CSS, and JavaScript control surface.
- **Python bridge:** local AI and orchestration services on port `9897`.
- **Node bridge:** HTTP/API proxy on port `9899`.
- **MCP server:** an offline JSON-RPC server over stdio with workspace-bounded tools.
- **Self-hosted stack:** Docker Compose definitions for the backend, database, Redis, gateway, and optional services.
- **Hawking channel:** one local-first encrypted channel boundary with explicit trust verification.
- **Repository registry:** provider-neutral, symmetric integration metadata for participating repositories.

## Development checks

```bash
python3 scripts/validate-runtime-coherence.py
python3 scripts/report-dashboard-duplicates.py
node frontend/scripts/test-sghv119-ownership.js
bash scripts/local-ci.sh
```

The local CI checks are offline-first and fail closed. They do not install packages, contact providers, publish artifacts, create keys, or modify the dashboard during validation.

## Network and deployment modes

The default runtime is offline and loopback-only. Networked modes are explicit deployment-owner policy:

| Mode | Behavior |
| --- | --- |
| `offline` / `LOCAL` | Default. Loopback-only; no external or LAN requests. |
| `hybrid` / `HYBRID` | Loopback plus explicitly authorized hosts. |
| `online` / `ONLINE` | Remote traffic only when explicitly enabled by deployment policy. |

Provider selection is configurable and remains the deployment owner’s choice. Missing or unauthorized capabilities must report `UNAVAILABLE`, `DENY`, or `REQUIRE_APPROVAL` rather than silently substituting another provider.

## Security and ownership

- Do not commit credentials, API keys, certificates, private keys, or private state.
- Keep core workflows functional without external services where possible.
- Use loopback-only development defaults and explicit consent for networked operation.
- Do not treat a listed repository as authorized or active without a real contract and health check.
- Preserve the dedicated branch rule and use pull requests for review.
- Review [SECURITY.md](SECURITY.md), [offline runtime policy](docs/OFFLINE_RUNTIME.md), and [runtime coherence](docs/architecture/RUNTIME_COHERENCE.md) before deployment.
