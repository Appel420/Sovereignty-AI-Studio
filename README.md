# Sovereignty AI Studio ⚔️

[![CI](https://github.com/Appel420/Sovereignty-AI-Studio/workflows/CI/badge.svg)](https://github.com/Appel420/Sovereignty-AI-Studio/actions)
[![codecov](https://codecov.io/gh/Appel420/Sovereignty-AI-Studio/branch/main/graph/badge.svg)](https://codecov.io/gh/Appel420/Sovereignty-AI-Studio)

> **Zero third-party vendor lock-in. No Google. No Meta. No Llama.cpp. No Vercel.**
> All AI inference is local and stays on your infrastructure.

**Private Sovereign AI Research and Production Platform**

**Core Model:** Super Grok Heavy 4.2 (xAI) – Locked, Sealed, Sovereign
**Authority:** Derek Appel
**Last Updated:** June 1, 2026

---

## Overview

Sovereignty AI Studio is a fully private, self-contained research and production environment for advanced sovereign artificial intelligence systems.

The platform integrates specialized domains including computer vision, logical reasoning, biomedical signal processing, cryptographic vaulting, autonomous agents, and system orchestration. All core services are intended to route through the project’s own runtime configuration, bridge services, and internal infrastructure.

No external services, third-party models, or internet connectivity are required for core operation.

---

## Architecture

```
Browser / iPhone
   │
   ├─── HTTP GET /SGHv119.html  ──► KODER frontend (static server / reverse proxy)
   │
   └─── API / WebSocket ────────► node-bridge (gateway)
                                    │ proxy
                                    ▼
                             Python bridge.py
                                    │
                                    ▼
                              backend (FastAPI, internal)
                                 ┌──┴──────────────┐
                                 ▼                 ▼
                           PostgreSQL         Redis
```

The UI should use runtime-configured endpoints rather than hardcoded hostnames or ports. Prefer relative paths or injected config for browser-facing calls.

### Runtime Config

Use `window.__SG_CONFIG` or `localStorage.sg_config` to provide runtime endpoints such as:

```json
{
  "nodeBase": "/api/node",
  "bridgeHealth": "/api/node/health",
  "bridgeChat": "/api/node/chat",
  "authBase": "/api/auth"
}
```

---

## Port / Service Model

| Service | Notes |
|---------|------|
| KODER frontend | Static UI; should not hardcode a host |
| node-bridge | Gateway; should read config from env/runtime |
| Python bridge | Internal AI bridge |
| backend (FastAPI) | Internal API, routed via bridge |
| PostgreSQL | Internal |
| Redis | Internal |

---

## Prerequisites

- Python 3.12.x
- Node.js >= 20.0.0 for bridge and unified servers
- Docker + Docker Compose for containerized workflows

---

## Quick Start

```bash
cp .env.example .env
# Configure runtime endpoints, secrets, TLS, auth, and database values in .env

docker compose up -d

# Check health through the bridge
curl /api/node/health
```

---

## Key Components

| Path | Purpose |
| --- | --- |
| `SGHv119.html` | Main sovereign dashboard |
| `node-bridge/server.js` | Node.js bridge proxy |
| `bridge.py` | Python bridge server |
| `frontend/src/services/alertApi.ts` | Runtime-configured API client |
| `backend/app/api/v1` | FastAPI endpoints |
| `docs/` | Documentation |

---

## Frontend / Dashboard Guidance

Frontend and dashboard code should:

- Use runtime config, not hardcoded localhost/127.0.0.1 literals
- Prefer relative paths for same-origin requests
- Use `authBase`, `nodeBase`, and `bridgeHealth` from config when present
- Avoid direct calls to fixed ports unless explicitly required by the runtime environment

---

## Usage

### Creating Alerts via API

```bash
curl -X POST "/api/node/api/v1/alerts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "security",
    "title": "Unauthorized Access",
    "message": "Failed login attempt detected",
    "severity": "high"
  }'
```

### WebSocket Connection

If enabled by runtime config, connect to the bridge WebSocket endpoint from the configured base URL. Do not hardcode localhost in browser code.

---

## Testing

```bash
make test
make lint
make clean
```
