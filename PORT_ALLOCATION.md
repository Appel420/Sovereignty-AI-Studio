# Sovereignty AI Studio - Port Allocation Guide

## Dashboard Architecture - Single Port 9898

### Overview

**Sovereignty AI Studio uses a centralized dashboard architecture where ALL external traffic goes through port 9898.** This design provides:

- **Single Entry Point**: Only one port (9898) needs to be exposed externally
- **Simplified Security**: Firewall and security rules only need to manage one port
- **Unified Access**: All services accessible through the dashboard
- **Organization Standard**: Consistent with organizational requirements

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL CLIENTS                          │
│         (Web Browsers, Mobile Apps, CLI Tools)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ ALL TRAFFIC
                         ▼
                  ┌──────────────┐
                  │   PORT 9898  │ ◄─── DASHBOARD (Only External Port)
                  │  Node Bridge │
                  │   (Gateway)  │
                  └──────┬───────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
   ┌───────────┐  ┌───────────┐  ┌───────────┐
   │ Backend   │  │  Weather  │  │   Other   │
   │ Port 8000 │  │ Port 8001 │  │ Services  │
   │(Internal) │  │(Internal) │  │(Internal) │
   └─────┬─────┘  └───────────┘  └───────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│  DB    │ │ Redis  │
│ :5432  │ │ :6379  │
│(Int)   │ │ (Int)  │
└────────┘ └────────┘
```

## Port Allocation

### External Port (Public Facing)

| Port | Service | Purpose | Access |
|------|---------|---------|--------|
| **9898** | **Dashboard/Node Bridge** | **All external traffic** | **PUBLIC** |

### Internal Ports (Docker Network Only)

| Port | Service | Purpose | Access |
|------|---------|---------|--------|
| 3000 | Frontend (React) | Development UI | Internal |
| 5432 | PostgreSQL | Database | Internal |
| 6379 | Redis | Cache | Internal |
| 8000 | Backend (FastAPI) | Primary API | Internal |
| 8001 | Weather (Quart) | Weather service | Internal |
| 8080 | Web App Server | apps/web | Internal |
| 8443 | Auth Proxy | WebSocket auth | Internal |
| 9000 | Unified Server | Primary server | Internal |

## Key Principle

🎯 **Everything connects to port 9898**

- Users connect to: `http://localhost:9898` or `http://your-domain:9898`
- Frontend accesses API via: `http://localhost:9898/api/v1/*`
- Weather accessed via: `http://localhost:9898/api/weather*`
- WebSocket connections: `ws://localhost:9898/ws/alerts`
- Health checks: `http://localhost:9898/health`

## Service Descriptions

### Port 9898 - Dashboard/Node Bridge ⭐ (ONLY EXTERNAL PORT)

**Purpose**: Centralized dashboard and API gateway - single entry point for all external traffic

**Technology**: Node.js Express + WebSocket

**Features**:
- Proxies `/api/v1/*` to Backend (8000)
- Proxies `/api/weather*` to Weather (8001)
- WebSocket at `/ws/alerts`
- Aggregated health at `/api/bridge/status`
- CORS management
- Request logging

**Access URLs**:
- Main Dashboard: `http://localhost:9898`
- Health Check: `http://localhost:9898/health`
- API Gateway: `http://localhost:9898/api/v1/*`
- Weather API: `http://localhost:9898/api/weather*`
- WebSocket: `ws://localhost:9898/ws/alerts`

**Environment Variables**:
```bash
NODE_BRIDGE_PORT=9898
BACKEND_URL=http://backend:8000    # Internal Docker network
WEATHER_URL=http://backend:8001    # Internal Docker network
CORS_ORIGIN=http://localhost:9898
```

### Port 8000 - Backend (FastAPI)

**Purpose**: Primary REST API backend (Internal only)

**Access**: Only through dashboard at `http://localhost:9898/api/v1/*`

**Direct Access**: Not exposed externally in Docker mode

### Port 8001 - Weather Dashboard (Quart)

**Purpose**: Weather API service (Internal only)

**Access**: Only through dashboard at `http://localhost:9898/api/weather*`

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
      - "9898:9898"  # ONLY external port
    environment:
      - BACKEND_URL=http://backend:8000
      - WEATHER_URL=http://backend:8001

  backend:
    expose:
      - "8000"  # Internal only

  db:
    expose:
      - "5432"  # Internal only
```

### Local Development

File: `.env`

```bash
# Dashboard - external facing
NODE_BRIDGE_PORT=9898

# Internal services
BACKEND_PORT=8000
WEATHER_PORT=8001

# Access everything through dashboard
BACKEND_URL=http://localhost:9898/api/v1
WEATHER_URL=http://localhost:9898/api/weather
```

### Frontend Configuration

File: `frontend/.env`

```bash
# Frontend connects ONLY to dashboard
REACT_APP_API_URL=http://localhost:9898/api/v1
REACT_APP_WS_URL=ws://localhost:9898
```

## Running Services

### Start with Docker (Recommended)

```bash
# Everything accessible through port 9898
docker-compose up

# Access dashboard
open http://localhost:9898
```

### Start with Scripts

```bash
# Start all services with dashboard on 9898
./start-all.sh

# Everything routes through dashboard
curl http://localhost:9898/health
curl http://localhost:9898/api/v1/mobile/status
curl http://localhost:9898/api/weather?city=London
```

## Testing Connectivity

All testing goes through port 9898:

```bash
# Dashboard health
curl http://localhost:9898/health

# Backend API (via dashboard)
curl http://localhost:9898/api/v1/mobile/status

# Weather API (via dashboard)
curl http://localhost:9898/api/weather?city=London

# Aggregated health
curl http://localhost:9898/api/bridge/status

# WebSocket connection
wscat -c ws://localhost:9898/ws/alerts
```

## Firewall Configuration

Only one port needs to be open:

```bash
# Allow port 9898 (dashboard)
sudo ufw allow 9898/tcp

# That's it! No other ports need external access
```

## Production Deployment

### Single Port Exposure

```nginx
# Nginx reverse proxy
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:9898;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Compose Production

```yaml
services:
  node-bridge:
    ports:
      - "9898:9898"  # Only port exposed to host
    environment:
      - BACKEND_URL=http://backend:8000
      - WEATHER_URL=http://backend:8001
    restart: always
```

## Benefits of Dashboard Architecture

1. **Simplified Security**: Only one port to secure and monitor
2. **Unified Access Control**: All authentication/authorization at one point
3. **Easy Load Balancing**: Single entry point for traffic distribution
4. **Simplified Firewall Rules**: One rule instead of many
5. **Consistent API Gateway**: All requests logged and monitored in one place
6. **Organizational Compliance**: Meets requirements for centralized access

## Troubleshooting

### Can't Connect to Services

**Solution**: Always use port 9898

```bash
# ✅ Correct
curl http://localhost:9898/api/v1/health
curl http://localhost:9898/api/weather?city=London

# ❌ Wrong (these ports not exposed externally)
curl http://localhost:8000/health
curl http://localhost:8001/api/weather
```

### Port 9898 Already in Use

```bash
# Find what's using port 9898
lsof -i :9898
netstat -tunlp | grep 9898

# Stop the conflicting service
kill -9 $(lsof -t -i:9898)
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

Services should use Docker service names (e.g., `http://backend:8000`, not `http://localhost:8000`)

## Migration Guide

### From Multi-Port to Dashboard Architecture

If you have existing code connecting to multiple ports:

```javascript
// OLD - Multiple ports
const backendUrl = 'http://localhost:8000/api/v1';
const weatherUrl = 'http://localhost:8001/api/weather';

// NEW - Dashboard only
const backendUrl = 'http://localhost:9898/api/v1';
const weatherUrl = 'http://localhost:9898/api/weather';
```

### Environment Variables

Update your `.env` files:

```bash
# OLD
BACKEND_URL=http://localhost:8000
WEATHER_URL=http://localhost:8001

# NEW - Everything through dashboard
BACKEND_URL=http://localhost:9898/api/v1
WEATHER_URL=http://localhost:9898/api/weather
```

## References

- Docker Compose: `/docker-compose.yml`
- Environment Template: `/.env.example`
- Node Bridge: `/node-bridge/server.js`
- Startup Script: `/start-all.sh`

## Summary

🎯 **One Port to Rule Them All: 9898**

- External clients connect only to port 9898
- All services accessible through the dashboard
- Internal services isolated on Docker network
- Simplified security and management
- Compliant with organizational standards

**Remember**: Port 9898 is your dashboard. Everything goes through it.
