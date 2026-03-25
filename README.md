# Sovereignty AI Studio ⚔️

> **Zero third-party vendor lock-in. No OpenAI. No Anthropic. No Google. No Meta. No Vercel.**  
> All AI inference is local and stays on your infrastructure.

---

## Architecture (single external port)

```
Port 9898 (ONLY external port)
     │
     ▼
node-bridge (WebSocket + HTTP gateway)
     │
     ▼
backend (FastAPI on 8000, internal)
     │
 ┌───┴───────────────┐
 ▼                   ▼
PostgreSQL (5432)   Redis (6379)
```

All host traffic enters through **port 9898**. Backend, database, and Redis remain on the internal Docker network.

---

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env
# Edit .env — set JWT_SECRET, database passwords, model paths

# 2. Start the full self-hosted stack
docker compose up -d

# 3. Check health
curl http://localhost:9898/health
```

**Services started**

| Service | Port | Notes |
|---------|------|-------|
| node-bridge (gateway) | 9898 | Only external port |
| backend (FastAPI) | internal | Routed via node-bridge |
| PostgreSQL 16 | internal | Initializes from `db/schema.sql` |
| Redis 7 | internal | Cache + session store |

For production with TLS and static assets, enable the bundled Nginx reverse proxy:

```bash
docker compose --profile production up -d
```

---

## Key Components

| Path | Purpose |
| --- | --- |
| `ai_core/sovereign_bridge.py` | Python sovereign AI bridge — routes all inference locally |
| `node-bridge/server.js` | Node.js WebSocket + HTTP bridge (port 9898) |
| `bridge.py` | Python WebSocket bridge server |
| `db/schema.sql` | Postgres schema (users, orgs, memberships, projects, usage, audit) |
| `backend/app/api/v1` | FastAPI endpoints (auth, orgs, media, voice, telemetry, etc.) |
| `frontend/src/views` | React views, including organization management |
| `docs/` | Hardware and research documentation |
| `docker-compose.yml` | Self-hosted stack (Postgres, Redis, Backend, Bridge, Nginx) |

---

## Sovereignty One Water Systems

The `firmware/esp32_controller.ino` controls a CDI+MED hybrid water purification system:
- Pump control based on PV voltage + TDS thresholds
- Anti-scaling polarity reversal every 15 minutes
- Safety interlocks (over-pressure, over-temperature)
- 1 Hz JSON telemetry via Serial

See [docs/sovereignty_one.md](docs/sovereignty_one.md) for full technical documentation.

---

*From Hello to Goodbye — Sovereignty AI Studio is a sovereign platform for the people.*
