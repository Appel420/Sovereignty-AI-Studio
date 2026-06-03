# Sovereignty AI Studio - Port Allocation Guide

## Dashboard Architecture — Three External Ports

### Overview

**Sovereignty AI Studio uses three service roles; browser clients should use runtime-configured HTTP endpoints:**

- **9898** — KODER frontend static host (local/dev convenience)
- **9899** — Node.js node-bridge HTTP/API gateway
- **9897** — Python bridge.py backend (internal to bridge path)

### Runtime Bridge Configuration (public-safe / iPhone-safe)

Browser-facing code should not hardcode `localhost`, `127.0.0.1`, or LAN literals.

Use runtime config instead:

```html
<script>
  window.__SG_CONFIG = {
    pythonBase: '/api/python',
    nodeBase: '/api/node',
    bridgeHealth: '/api/node/health',
    bridgeChat: '/api/node/chat',
    disableWebSocket: true
  };
</script>
```

Or persist equivalent JSON in `localStorage.sg_config`.

- Default recommended browser endpoints are relative (`/api/python`, `/api/node`) so HTTPS pages stay same-origin.
- If the frontend is HTTPS, bridge targets must also be HTTPS (or same-origin reverse-proxied HTTPS paths).
- WebSocket is optional; HTTP bridge path is the default and supported mode.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL CLIENTS                          │
│         (Web Browsers, Mobile Apps — iPhone)                 │
└──────────┬────────────────────────────┬─────────────────────┘
           │ HTTP — Load UI              │ WebSocket / HTTP API
           ▼                             ▼
    ┌──────────────┐              ┌──────────────┐
    │   PORT 9898  │              │   PORT 9899  │
    │ KODER frontend│              │  node-bridge │
    │ (SGHv119.html)│              │  (server.js) │
    └──────────────┘              └──────┬───────┘
                                         │ proxy
                                         ▼
                                  ┌──────────────┐
                                  │   PORT 9897  │ ◄─── Python bridge.py
                                  │   (PRIMARY)  │      AI / TTS / STT
                                  └──────┬───────┘
                                         │
                 ┌───────────────┬────────┴───────┬───────────────┐
                 ▼               ▼                ▼               ▼
          ┌───────────┐  ┌───────────┐  ┌──────────────┐  ┌───────────┐
          │ FastAPI   │  │  Gateway  │  │   Keycloak   │  │   Redis   │
          │ Port 8002 │  │ Port 9001 │  │ :8080→:8443  │  │ Port 6379 │
          │(Internal) │  │(Internal) │  │  SSO/Identity│  │(Internal) │
          └─────┬─────┘  └───────────┘  └──────────────┘  └───────────┘
                │
           ┌────┴─────┐
           ▼           ▼
      ┌─────────┐  ┌─────────┐
      │ Postgres│  │ Weather │
      │  :5432  │  │  :8001  │
      │(Internal)│  │(Internal)│
      └─────────┘  └─────────┘
```

## Port Architecture

### Port Assignments

| Port | Service | Role | Access |
|------|---------|------|--------|
| **9898** | **KODER Frontend (SGHv119.html)** | **UI served here — iPhone/browser loads the page** | **PUBLIC** |
| **9899** | **Node.js node-bridge (server.js)** | **WebSocket + HTTP API gateway (browser connects here)** | **PUBLIC** |
| **9897** | **Python bridge.py (WebSocket)** | **PRIMARY AI/TTS/STT backend** | Internal |

### Internal Ports (Docker Network Only)

| Port | Service | Purpose | Access |
|------|---------|---------|--------|
| 3000 | Frontend (React) | Development UI | Internal |
| 5432 | PostgreSQL | Database | Internal |
| 6379 | Redis | Cache | Internal |
| 8001 | Weather (Quart) | Weather service | Internal |
| 8002 | Backend (FastAPI) | Primary API | Internal |
| 8080 | Keycloak SSO | SSO / Identity (host port, maps to :8443 inside container) | Internal |
| 8443 | Keycloak HTTPS | Keycloak container-internal HTTPS port | Internal |
| 9001 | Multi-agent Gateway | Internal orchestration | Internal |
| 9002 | Judge Metrics | Prometheus scrape target | Internal |

> ⛔ **BANNED**: Ports 8000 and 9000 are never used. Any service previously on these ports is now on 8002 and 9001 respectively.

## Key Principle

🎯 **UI can load from any HTTPS origin — bridge traffic should use runtime-configured HTTP endpoints**

- Load dashboard from your deployment origin (example): `https://your-domain.example/SGHv119_Newest.html`
- Bridge health: `/api/node/health`
- Bridge chat: `/api/node/chat`
- API requests: `/api/node/api/v1/*`
- Python bridge route (if exposed via proxy): `/api/python/*`

## Service Descriptions

### Port 9898 - KODER Frontend ⭐ (UI entry point)

**Purpose**: KODER dashboard (SGHv119.html) — what iPhones and browsers load.

**Technology**: Static HTML dashboard (local `python3 -m http.server` or production reverse proxy/CDN)

**Features**:
- Primary dashboard HTML served to all clients
- Browser uses HTTP API routes through node-bridge (WebSocket optional)
- node-bridge proxies AI/TTS/STT messages to Python bridge.py on port **9897**

### Port 9897 - Python bridge.py ⭐ (PRIMARY backend)

**Purpose**: Main Python backend. Handles AI chat, TTS, memory, STT.

**Technology**: Python asyncio WebSocket server

### Port 9899 - Node.js node-bridge (BACKUP only)
- Aggregated health at `/api/bridge/status`
- CORS management
- Request logging

**Access URLs**:
- Load UI: `http://localhost:9898/SGHv119.html`
- WebSocket bridge: `ws://localhost:9899/`
- Health Check: `http://localhost:9899/health`
- API Gateway: `http://localhost:9899/api/v1/*`
- Weather API: `http://localhost:9899/api/weather*`
- WebSocket alerts: `ws://localhost:9899/ws/alerts`

**Environment Variables**:
```bash
NODE_BRIDGE_PORT=9899
BACKEND_URL=http://backend:8002    # Internal Docker network
WEATHER_URL=http://backend:8001    # Internal Docker network
CORS_ORIGIN=http://localhost:9898
```

### Port 8002 - Backend (FastAPI)

**Purpose**: Primary REST API backend (Internal only)

**Access**: Only through node-bridge at `http://localhost:9899/api/v1/*`

**Direct Access**: Not exposed externally in Docker mode

### Port 8001 - Weather Dashboard (Quart)

**Purpose**: Weather API service (Internal only)

**Access**: Only through node-bridge at `http://localhost:9899/api/weather*`

**Direct Access**: Not exposed externally in Docker mode

### Other Internal Services

All other services run on internal Docker network and are not directly accessible from outside.

## Configuration Examples

### Docker Environment (Recommended)

File: `docker-compose.yml`

```yaml
services:
  node-bridge:
    ports:
      - "9899:9899"  # WS + API proxy
    environment:
      - BACKEND_URL=http://backend:8002
      - WEATHER_URL=http://backend:8001

  backend:
    expose:
      - "8002"  # Internal only

  db:
    expose:
      - "5432"  # Internal only
```

### Local Development

File: `.env`

```bash
# Port assignments
NODE_BRIDGE_PORT=9899
SG_PORT=9897
BACKEND_PORT=8002
WEATHER_PORT=8001

# Internal service URLs (used by node-bridge → backend)
BACKEND_URL=http://localhost:8002
WEATHER_URL=http://localhost:8001
```

### Frontend Configuration

File: `frontend/.env`

```bash
# Frontend (KODER) is served at 9898; API/WS traffic targets node-bridge on 9899
REACT_APP_API_URL=http://localhost:9899/api/v1
REACT_APP_WS_URL=ws://localhost:9899
```

## Running Services

### Start with START_SERVER.sh (Recommended for local)

```bash
./START_SERVER.sh

# Load KODER dashboard
open http://localhost:9898/SGHv119.html

# API / WS traffic (browser → node-bridge)
curl http://localhost:9899/health
```

### Start with Docker

```bash
docker-compose up

# KODER frontend is served separately (non-Docker):
python3 -m http.server 9898 --bind 127.0.0.1 --directory .
open http://localhost:9898/SGHv119.html

# node-bridge WS/API:
curl http://localhost:9899/health
```

## Testing Connectivity

```bash
# node-bridge health
curl http://localhost:9899/health

# Backend API (via node-bridge)
curl http://localhost:9899/api/v1/mobile/status

# Weather API (via node-bridge)
curl http://localhost:9899/api/weather?city=London

# Aggregated bridge health
curl http://localhost:9899/api/bridge/status

# WebSocket connection (node-bridge)
wscat -c ws://localhost:9899/ws/alerts

# Load KODER frontend
curl http://localhost:9898/SGHv119.html
```

## Firewall Configuration

Two ports need to be open externally:

```bash
# Allow KODER frontend
sudo ufw allow 9898/tcp

# Allow node-bridge (WS + API)
sudo ufw allow 9899/tcp
```

## Production Deployment

### Reverse Proxy

```nginx
# Nginx reverse proxy
server {
    listen 80;
    server_name your-domain.com;

    # Serve KODER static files
    location / {
        proxy_pass http://localhost:9898;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Proxy WS + API to node-bridge
    location /api/ {
        proxy_pass http://localhost:9899;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /ws {
        proxy_pass http://localhost:9899;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Compose Production

```yaml
services:
  node-bridge:
    ports:
      - "9899:9899"  # WS + API proxy exposed to host
    environment:
      - BACKEND_URL=http://backend:8002
      - WEATHER_URL=http://backend:8001
```

## Benefits of Three-Port Architecture

1. **Clear separation**: UI (9898), API/WS proxy (9899), AI backend (9897)
2. **Unified API gateway**: All REST + WS from the browser go through node-bridge on 9899
3. **Frontend isolation**: Static file server on 9898 is independent of backend services
4. **Python-first AI**: bridge.py on 9897 is the primary AI/TTS/STT handler

## Troubleshooting

### Can't load KODER dashboard

```bash
# ✅ Correct — load the HTML from the static file server
open http://localhost:9898/SGHv119.html

# ❌ Wrong — node-bridge doesn't serve static assets
open http://localhost:9899
```

### API or WebSocket not connecting

```bash
# ✅ Correct — API + WS go to node-bridge
curl http://localhost:9899/health
wscat -c ws://localhost:9899

# ❌ Wrong — 9898 is only the static file server
curl http://localhost:9898/health
```

### Port already in use

```bash
# Find and stop what's using the port
lsof -i :9898
lsof -i :9899
lsof -i :9897
kill -9 $(lsof -t -i:9898)
kill -9 $(lsof -t -i:9899)
kill -9 $(lsof -t -i:9897)
```

### Docker Services Not Accessible

Check that node-bridge is running:

```bash
docker-compose ps
docker-compose logs node-bridge
```

### Internal Services Can't Reach Each Other

Verify Docker network:

```bash
docker network inspect sovereignty-ai-studio_default
```

Services should use Docker service names (e.g., `http://backend:8002`, not `http://localhost:8002`)

## Migration Guide

### From Old 9898-only Architecture to Three-Port Architecture

If you have existing code pointing everything at 9898:

```javascript
// OLD - everything through 9898
const backendUrl = 'http://localhost:9898/api/v1';
const wsUrl = 'ws://localhost:9898';

// NEW - UI from 9898, API/WS from node-bridge on 9899
const uiUrl   = 'http://localhost:9898/SGHv119.html';  // load KODER
const apiUrl  = 'http://localhost:9899/api/v1';         // API calls
const wsUrl   = 'ws://localhost:9899';                  // WebSocket
```

### Environment Variables

```bash
# Current correct values
NODE_BRIDGE_PORT=9899        # node-bridge WS + API proxy
SG_PORT=9897                 # Python bridge.py AI backend
BACKEND_URL=http://localhost:8002   # direct backend (internal, never use 8000)
```

## References

- Docker Compose: `/docker-compose.yml`
- Environment Template: `/.env.example`
- Node Bridge: `/node-bridge/server.js`
- Startup Script: `/START_SERVER.sh`

## Summary

🎯 **Three ports, three roles:**

| Port | What you do with it |
|------|---------------------|
| **9898** | Open this in your browser to load the KODER dashboard |
| **9899** | Browser connects here for all WebSocket and API traffic |
| **9897** | Python AI backend — node-bridge proxies to here |

- Internal services (FastAPI, DB, Redis) stay on the Docker network only.
- bridge.py and the static file server are started by `START_SERVER.sh` (non-Docker).
