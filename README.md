# Sovereignty AI Studio ⚔️

> **Zero third-party vendor lock-in. No Ollama. No Google. No Meta. No Vercel. No OpenAI.**
> All AI inference is local. All data stays on your infrastructure.

---

## Architecture

```
Port 9898 (ONLY external port)
     │
     ▼
node-bridge/sovereign_bridge.mjs   ← WebSocket + HTTP gateway
     │
     ▼
ai_core/sovereign_bridge.py        ← Sovereign AI router
     ├── local_gguf (llama-cpp-python)
     ├── local_onnx (onnxruntime)
     └── sovereign_api (self-hosted endpoint)
     │
     ▼
Backend FastAPI (port 8000, internal)
     ├── backend/api/auth.py        ← JWT auth (Keycloak-compatible)
     ├── backend/api/org.py         ← Org + membership CRUD
     ├── backend/api/project.py     ← Project + permission CRUD
     ├── backend/api/dashboard.py   ← Security dashboard API
     └── backend/roles/roles_registry.py ← RBAC (all role tiers)
     │
     ├── Postgres 16 (port 5432, internal)  ← db/schema.sql
     └── Redis 7    (port 6379, internal)
```

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env
# Edit .env — set JWT_SECRET, SOVEREIGN_MODEL_PATH, database passwords

# 2. Start the full self-hosted stack
docker compose up -d

# 3. Check health
curl http://localhost:9898/health
```

## Key Components

| File/Directory | Purpose |
|---|---|
| `ai_core/sovereign_bridge.py` | Python sovereign AI bridge — routes all inference locally |
| `ai_core/providers/local_inference.py` | GGUF (llama-cpp-python) + ONNX local model providers |
| `ai_core/providers/sovereign_api.py` | Self-hosted API provider (JWT, no SaaS) |
| `node-bridge/sovereign_bridge.mjs` | Node.js WebSocket + HTTP bridge (port 9898) |
| `bridge.py` | Python WebSocket bridge server |
| `db/schema.sql` | Full Postgres schema (users, orgs, memberships, projects, usage, audit) |
| `db/connector.py` | psycopg2 Postgres connector (no ORM) |
| `backend/api/org.py` | Org CRUD + membership management |
| `backend/api/project.py` | Project CRUD + permission management |
| `backend/api/auth.py` | JWT auth with Keycloak integration |
| `backend/api/dashboard.py` | Security dashboard API |
| `backend/roles/roles_registry.py` | All role definitions + RBAC middleware |
| `analytics/usage_tracker.py` | AI call + token usage tracking |
| `analytics/audit_logger.py` | Immutable append-only audit log |
| `firmware/esp32_controller.ino` | ESP32 CDI/MED hybrid water system controller |
| `docs/sovereignty_one.md` | Sovereignty One technical documentation |
| `docs/sdt_boron_therapy.md` | SDT-Boron therapy preclinical research |
| `frontend/index.html` | Main dashboard documentation page |
| `docker-compose.yml` | Self-hosted stack (Postgres, Redis, Backend, Bridge, Nginx) |

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `JWT_SECRET` | Secret for JWT signing | Yes |
| `DATABASE_URL` | Postgres connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SOVEREIGN_MODEL_PATH` | Path to GGUF model file | For local inference |
| `SOVEREIGN_ONNX_PATH` | Path to ONNX model file | For ONNX inference |
| `SOVEREIGN_API_URL` | Self-hosted API endpoint | For API provider |
| `KEYCLOAK_URL` | Self-hosted Keycloak URL | For SSO |

See `.env.example` for complete documentation. **No third-party API keys required.**

## Role Tiers

| Role | Level | Category |
|---|---|---|
| System | 99 | System (full override) |
| Executive L5 | 5 | Executive |
| Intelligence L5 | 5 | Intelligence |
| Legal L5 | 5 | Legal |
| Military Commander | 5 | Military |
| Security Admin | 5 | Security |
| Government L4 | 4 | Government |
| Intelligence L4 | 4 | Intelligence |
| Legal L4 | 4 | Legal |
| Military Operator | 4 | Military |
| Finance Admin | 4 | Finance |
| Org Admin | 4 | General |
| Project Lead | 2 | General |
| Analyst | 2 | Intelligence |
| Finance | 3 | Finance |
| Member | 1 | General |
| Viewer | 0 | General |

## Sovereignty Principles

1. **No data leaves the infrastructure.** All AI inference is local.
2. **No vendor lock-in.** No Ollama, no OpenAI, no Anthropic, no Google, no Meta, no Vercel.
3. **Agents work in symmetry.** The sovereign bridge connects all subsystems.
4. **Self-hosted everything.** Postgres, Redis, Nginx, Keycloak — all on your infra.
5. **Immutable audit trail.** All actions logged to Postgres with no UPDATE/DELETE.

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
