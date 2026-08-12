[![CI](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ci.yml)   [![iOS Sovereign Build (local-first)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ios-sovereign-build.yml/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions/workflows/ios-sovereign-build.yml)
# Sovereignty AI Studio

@claude @codex @copilot @grok @duckai

This is the main dedicated branch. All changes by Claude Grok/Ara DuckAI GPT/Codex Copilot must be made in their dedicated branch. Do not push directly to main. Create a Pull Request for review.

Sovereignty AI Studio is a self-hosted, offline-first AI control surface and supporting service stack. The primary user interface is the KODER dashboard in [`SGHv119.html`](SGHv119.html); Python and Node services provide local routing, agent orchestration, and optional self-hosted integrations.

## Canonical runtime map

The repository uses one canonical runtime path:

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

## SGHv119 cleanup process

The monolithic dashboard is cleaned surgically. Existing visual markup, role cards, panels, styles, and controls are preserved.

1. Establish the canonical runtime manifest.
2. Load the shared transport, Hawking channel, integration, and bootstrap modules exactly once.
3. Remove inline Hawking managers and duplicate status creation.
4. Remove duplicate bridge retry, keepalive, and fallback ownership.
5. Permit approved loopback transport in local/offline mode; block only unauthorized external transport.
6. Require trusted fingerprints for remote Hawking envelopes.
7. Validate ownership with `frontend/scripts/test-sghv119-ownership.js`.
8. Run the complete local CI suite before enabling another adapter or repository.

A dashboard status may report `DECLARED`, `CONFIGURED`, `AVAILABLE`, `VERIFIED`, `ACTIVE`, `UNAVAILABLE`, `DENY`, or `REQUIRE_APPROVAL`. It must not claim that a certificate, socket, repository, provider, cryptographic adapter, or security service is active merely because a label or file exists.

## Quick start

### Local development

Requirements:

- Python 3.13 or later
- Node.js 24 or later

Install the checked-in runtime dependencies. This creates `.venv` and installs both Node workspaces; it does not create credentials, substitute a model, or make runtime network calls:

```bash
./INSTALL.sh
```

For an air-gapped workstation with pre-populated Python and npm caches, use:

```bash
./INSTALL.sh --offline
```

Then start the canonical local services:

```bash
./START_SERVER.sh
```

Open the dashboard at:

```text
http://127.0.0.1:9898/SGHv119.html
```

| Service | Address | Purpose |
| --- | --- | --- |
| KODER dashboard | `http://127.0.0.1:9898` | Static dashboard |
| Python bridge | `http://127.0.0.1:9897` | Local backend |
| Node bridge | `http://127.0.0.1:9899` | HTTP/API proxy |

Press `Ctrl+C` in the launcher terminal to stop all services.

### MCP server

The MCP server works without network access or API keys:

```bash
python3 mcp_server.py
```

It defaults to `SG_MCP_MODE=offline`. Set `SG_MCP_WORKSPACE` to restrict a client to a specific directory. The MCP tools are bounded, read-only, and do not edit files or accept credentials.

### Container services

The self-hosted service stack is defined in [`docker-compose.yml`](docker-compose.yml). Review its required environment variables and production defaults before starting it:

```bash
docker compose up --build
```

## Network and deployment modes

The default runtime is offline and loopback-only. Networked modes are explicit deployment-owner policy:

| Mode | Behavior |
| --- | --- |
| `offline` | Default. Loopback-only; no external or LAN requests. |
| `hybrid` | Loopback plus explicitly authorized hosts. |
| `online` | Remote traffic only when explicitly enabled by deployment policy. |

Provider selection is configurable and remains the deployment owner’s choice. The project does not impose a universal vendor or model ban. Missing or unauthorized capabilities must report `UNAVAILABLE`, `DENY`, or `REQUIRE_APPROVAL` rather than silently substituting another provider.

For air-gapped or local-network deployments, configure a private local CA and verify TLS/WSS at runtime. Public certificate automation is an explicit deployment option, not proof that local development is encrypted.

## Development checks

```bash
python3 scripts/validate-runtime-coherence.py
python3 scripts/report-dashboard-duplicates.py
node frontend/scripts/test-sghv119-ownership.js
bash scripts/local-ci.sh
```

The checks are local-only. They do not use a hosted runner, publish artifacts, create keys, contact a provider, or modify the dashboard.

## Repository layout

```text
SGHv119.html                         Canonical dashboard
START_SERVER.sh                      Canonical local launcher
bridge.py                            Python local bridge
node-bridge/                         Node HTTP/API bridge
frontend/runtime/                    Shared transport and Hawking boundaries
integration/                          Repository and trust manifests
config/runtime-coherence.json        Canonical runtime map
backend/                             FastAPI backend services
gateway/                             Python multi-agent gateway
agents/                              Agent service definitions
mcp_server.py                        Offline MCP server
docs/                                Architecture and deployment documentation
external/                            Vendored third-party source; excluded from runtime
```

## Security and ownership

- Do not commit credentials, API keys, certificates, private keys, or private state.
- Keep core workflows functional without external services where possible.
- Use loopback-only development defaults and explicit consent for networked operation.
- Do not treat a listed repository as authorized or active without a real contract and health check.
- Preserve the dedicated branch rule and use pull requests for review.
- Review [SECURITY.md](SECURITY.md), [offline runtime policy](docs/OFFLINE_RUNTIME.md), and [runtime coherence](docs/architecture/RUNTIME_COHERENCE.md) before deployment.
