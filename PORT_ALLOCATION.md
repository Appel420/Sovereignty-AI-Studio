# Sovereignty AI Studio - Port Allocation Guide

## Overview

This document defines the standardized port allocation for all services in the Sovereignty AI Studio ecosystem. Following these port assignments ensures there are no conflicts between services when running locally, in Docker, or in production environments.

## Port Allocation Table

| Port | Service | Type | Configuration | Status |
|------|---------|------|---------------|--------|
| **3000** | Frontend (React) | Development | `FRONTEND_PORT` | ✅ Standard |
| **5432** | PostgreSQL | Database | Docker default | ✅ Standard |
| **6379** | Redis | Cache | Docker default | ✅ Standard |
| **8000** | Backend (FastAPI) | API | `BACKEND_PORT` | ✅ **Primary Backend** |
| **8001** | Weather Dashboard | Python/Quart | `WEATHER_PORT` | ✅ Standard |
| **8080** | Web App Server | Node.js | `WEB_APP_PORT` | ✅ Standard |
| **8443** | Auth Proxy | WebSocket | `PORT_AUTH` | ✅ Standard |
| **9000** | Unified Server | Node.js | `PORT_UNIFIED` | ✅ **Primary Server** |
| **9898** | Node Bridge | Node.js | `NODE_BRIDGE_PORT` | ✅ **API Gateway** |

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Clients                          │
│            (Web Browsers, Mobile Apps, CLI)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │  Port 9898   │ ← Main Entry Point
              │  Node Bridge │ (API Gateway)
              └──────┬───────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   ┌─────────────┐      ┌─────────────┐
   │  Port 8000  │      │  Port 8001  │
   │   Backend   │      │   Weather   │
   │  (FastAPI)  │      │   (Quart)   │
   └──────┬──────┘      └─────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌────────┐
│Port5432│  │Port6379│
│PostgreSQL Redis   │
└────────┘  └────────┘

Additional Services:
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Port 3000  │  │  Port 8080  │  │  Port 9000  │
│  Frontend   │  │  Web App    │  │  Unified    │
│   (React)   │  │   Server    │  │   Server    │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Service Descriptions

### Port 3000 - Frontend (React Development Server)
- **Purpose**: React development server for the main web UI
- **Technology**: React 19 + TypeScript
- **Environment Variable**: `FRONTEND_PORT`
- **Default Command**: `npm start` (in `/frontend` directory)
- **Access**: http://localhost:3000

### Port 5432 - PostgreSQL Database
- **Purpose**: Primary database for persistent storage
- **Technology**: PostgreSQL 13
- **Environment Variable**: Part of `DATABASE_URL`
- **Docker Service**: `db`
- **Credentials**: `postgres/password` (change in production)

### Port 6379 - Redis Cache
- **Purpose**: Cache and session storage
- **Technology**: Redis 7
- **Environment Variable**: Part of `REDIS_URL`
- **Docker Service**: `redis`

### Port 8000 - Backend (FastAPI) ⭐
- **Purpose**: Primary REST API backend
- **Technology**: Python FastAPI + Uvicorn
- **Environment Variable**: `BACKEND_PORT`
- **Docker Service**: `backend`
- **Access**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Key Endpoints**:
  - `/health` - Health check
  - `/api/v1/*` - API endpoints
  - `/api/v1/mobile/status` - Mobile status

### Port 8001 - Weather Dashboard (Quart)
- **Purpose**: Weather API service
- **Technology**: Python Quart (async Flask)
- **Environment Variable**: `WEATHER_PORT`
- **Access**: http://localhost:8001
- **Key Endpoints**:
  - `/api/weather?city={city}` - Weather data
  - `/api/forecast?city={city}` - Weather forecast

### Port 8080 - Web App Server
- **Purpose**: Simple web app server for apps/web
- **Technology**: Node.js HTTP server
- **Environment Variable**: `WEB_APP_PORT`
- **Access**: http://localhost:8080
- **Key Endpoints**:
  - `/intent` - Intent processing

### Port 8443 - Auth Proxy
- **Purpose**: WebSocket authentication proxy
- **Technology**: Node.js WebSocket
- **Environment Variable**: `PORT_AUTH`
- **Part Of**: Unified Server

### Port 9000 - Unified Server ⭐
- **Purpose**: Primary enterprise server (production)
- **Technology**: Node.js + WebSocket
- **Environment Variable**: `PORT_UNIFIED`
- **Features**:
  - WebSocket bridge
  - Authentication
  - DDG integration
  - Piper TTS
- **Access**: http://localhost:9000
- **Health**: http://localhost:9000/health

### Port 9898 - Node Bridge (API Gateway) ⭐
- **Purpose**: Main API gateway and proxy
- **Technology**: Node.js Express + WebSocket
- **Environment Variable**: `NODE_BRIDGE_PORT`
- **Docker Service**: `node-bridge`
- **Access**: http://localhost:9898
- **Key Features**:
  - Proxies `/api/v1/*` to Backend (8000)
  - Proxies `/api/weather*` to Weather (8001)
  - WebSocket at `/ws/alerts`
  - Health aggregation at `/api/bridge/status`

## Environment Configuration

### Local Development (.env)
```bash
# Copy from .env.example
BACKEND_PORT=8000
WEATHER_PORT=8001
NODE_BRIDGE_PORT=9898
WEB_APP_PORT=8080
FRONTEND_PORT=3000

# Service URLs (localhost)
BACKEND_URL=http://localhost:8000
WEATHER_URL=http://localhost:8001
```

### Docker Environment (docker-compose.yml)
```yaml
# Service URLs use Docker service names
BACKEND_URL=http://backend:8000
WEATHER_URL=http://backend:8001
NODE_BRIDGE_PORT=9898
```

## Port Conflict Resolution History

### Previous Issues (Resolved)
1. **Critical Conflict**: Both `backend` and `node-bridge` were on port 9898
   - **Resolution**: Backend moved to 8000, node-bridge stays on 9898

2. **Invalid Port**: frontend/Dockerfile exposed port 98765 (invalid)
   - **Resolution**: Changed to 3000 (standard React port)

3. **Port Mismatch**: start-all.sh had all services defaulting to 9898
   - **Resolution**: Unique ports assigned with proper environment variables

4. **Web App Conflict**: apps/web/Server.js hardcoded to 9898
   - **Resolution**: Changed to 8080 with `WEB_APP_PORT` environment variable

## Running Services

### Start All Services (Development)
```bash
# Start with defaults
./start-all.sh

# Or with custom ports
BACKEND_PORT=8000 WEATHER_PORT=8001 NODE_BRIDGE_PORT=9898 ./start-all.sh
```

### Start with Docker Compose
```bash
docker-compose up
```

### Start Individual Services
```bash
# Backend (FastAPI)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Weather Dashboard
PYTHONPATH=.:./backend hypercorn weather_dashboard:app --bind 0.0.0.0:8001

# Node Bridge
cd node-bridge && NODE_BRIDGE_PORT=9898 node server.js

# Frontend
cd frontend && npm start

# Unified Server
node unified_server.js
```

## Testing Connectivity

```bash
# Backend
curl http://localhost:8000/health

# Weather
curl http://localhost:8001/api/weather?city=London

# Node Bridge
curl http://localhost:9898/health

# Aggregated Status
curl http://localhost:9898/api/bridge/status

# Frontend (in browser)
open http://localhost:3000

# Unified Server
curl http://localhost:9000/health
```

## Frontend Configuration

The frontend connects to services via environment variables:

```bash
# .env in /frontend directory
REACT_APP_API_URL=http://localhost:9898/api/v1
REACT_APP_WS_URL=ws://localhost:9898
```

## Production Considerations

1. **Port Security**: In production, bind services to specific interfaces
2. **Firewall Rules**: Only expose 9898 and 9000 externally
3. **TLS/SSL**: Use reverse proxy (nginx/caddy) for HTTPS
4. **Database**: Use managed PostgreSQL service
5. **Redis**: Use managed Redis or Redis Cluster
6. **Environment Variables**: Use secrets management (Vault, AWS Secrets Manager)

## Troubleshooting

### Port Already in Use
```bash
# Find what's using a port
lsof -i :9898
netstat -tunlp | grep 9898

# Kill process on port
kill -9 $(lsof -t -i:9898)
```

### Service Can't Connect
1. Check service is running: `curl http://localhost:{port}/health`
2. Check firewall rules: `sudo ufw status`
3. Check environment variables: `env | grep PORT`
4. Check Docker networking: `docker network inspect bridge`

### CORS Errors
- Ensure backend `cors_origins` in config.py includes your frontend URL
- Check NODE_BRIDGE_PORT matches CORS_ORIGIN in docker-compose.yml

## References

- Docker Compose: `/docker-compose.yml`
- Environment Template: `/.env.example`
- Backend Config: `/backend/app/config.py`
- Node Bridge: `/node-bridge/server.js`
- Unified Server: `/unified_server.js`
- Startup Script: `/start-all.sh`

## Change Log

- **2026-03-12**: Port allocation standardization
  - Backend: 9898 → 8000
  - Weather: 9898 → 8001
  - Frontend: 98765 → 3000
  - Web App: 9898 → 8080
  - Created comprehensive documentation
  - Added .env.example with full port configuration
