# Sovereignty AI Studio

Sovereignty AI Studio is a self-hosted, offline-first AI control surface and
supporting service stack. The primary user interface is the KODER dashboard in
[`SGHv119.html`](SGHv119.html); Python and Node services provide local routing,
agent orchestration, and optional self-hosted integrations.

## What is included

- **KODER dashboard:** a plain HTML, CSS, and JavaScript control surface.
- **Python bridge:** local AI and orchestration services on port `9897`.
- **Node bridge:** HTTP/API proxy on port `9899`.
- **MCP server:** an offline JSON-RPC server over stdio with workspace-bounded
  tools.
- **Self-hosted stack:** Docker Compose definitions for the backend, database,
  Redis, gateway, and optional services.

## Quick start

### Local development

Requirements:

- Python 3.11 or later
- Node.js 20 or later

From the repository root, install the required Python and Node dependencies
using your preferred environment manager, then start the local services:

```bash
./START_SERVER.sh
```

Open the dashboard at:

```text
http://127.0.0.1:9898/SGHv119.html
```

The launcher starts these loopback services:

| Service | Address | Purpose |
| --- | --- | --- |
| KODER dashboard | `http://127.0.0.1:9898` | Static dashboard |
| Python bridge | `http://127.0.0.1:9897` | Local backend |
| Node bridge | `http://127.0.0.1:9899` | HTTP/API proxy |

Press `Ctrl+C` in the launcher terminal to stop all three services.

### MCP server

The MCP server works without network access or API keys:

```bash
python3 mcp_server.py
```

It defaults to `SG_MCP_MODE=offline`. Set `SG_MCP_WORKSPACE` to restrict a
client to a specific directory. See the [MCP server source](mcp_server.py) for
the available tools and configuration.

### Container services

The self-hosted service stack is defined in
[`docker-compose.yml`](docker-compose.yml). Review its required environment
variables and production defaults before starting it:

```bash
docker compose up --build
```

## Network and deployment modes

The default runtime is offline and loopback-only. `SG_NETWORK_MODE` supports:

| Mode | Behavior |
| --- | --- |
| `offline` | Default. Loopback-only; no external or LAN requests. |
| `hybrid` | Loopback plus hosts explicitly listed in `SG_LOCAL_NETWORK_ALLOWLIST`. |
| `online` | Remote traffic only when `SG_ENABLE_REMOTE_NETWORK=1` is also set. |

The Node bridge binds to `127.0.0.1` by default. For LAN, device, or public
deployments, configure TLS and explicit access controls. The dashboard must
disclose network activity; bridge network status is available at
`/api/network/status`.

For air-gapped or local-network deployments, use a private local CA. Public
TLS through Let's Encrypt is an explicit online deployment option. Full details
are in [Offline runtime and transport policy](docs/OFFLINE_RUNTIME.md).

## Repository layout

```text
SGHv119.html       KODER dashboard
START_SERVER.sh    Local three-service launcher
bridge.py          Python local bridge
node-bridge/       Node HTTP/API bridge
backend/           FastAPI backend services
gateway/           Python multi-agent gateway
agents/            Agent service definitions
mcp_server.py      Offline MCP server
docs/              Architecture, deployment, and developer documentation
```

## Development checks

```bash
npm run check
make py-test
make py-lint
```

## Security

- Do not commit credentials, API keys, certificates, or `.env` files.
- Keep core workflows functional without external services where possible.
- Use loopback-only development defaults and explicit consent for networked
  operation.
- Review [SECURITY.md](SECURITY.md) and the
  [offline runtime policy](docs/OFFLINE_RUNTIME.md) before deployment.
