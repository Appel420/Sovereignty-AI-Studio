<< copilot/remove-external-platform-dependencies
# Sovereignty AI Studio ⚔️

> **Zero third-party vendor lock-in. No Ollama. No Google. No Meta. No Vercel. No OpenAI.**
> All AI inference is local. All data stays on your infrastructure.

---

## Architecture


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


## Quick Start

bash
# 1. Copy environment config
cp .env.example .env
# Edit .env — set JWT_SECRET, SOVEREIGN_MODEL_PATH, database passwords

# 2. Start the full self-hosted stack
docker compose up -d

# 3. Check health
curl http://localhost:9898/health


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
=======
# Sovereignty AI Studio

> A fully sovereign, self-hosted AI platform with multi-tenant workspaces, multi-provider AI routing, full audit trail, agent marketplace, and hardware integration — built to run on your infrastructure, owned by you.

---

## Table of Contents

1. [Quick Start (Docker)](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Subsystems](#subsystems)
   - [AI Studio](#ai-studio)
   - [Sovereignty One Hardware](#sovereignty-one-hardware)
   - [SDT-Boron Therapy Research](#sdt-boron-therapy-research)
4. [API Reference](#api-reference)
5. [Dashboard Roles](#dashboard-roles)
6. [Environment Variables](#environment-variables)
7. [Contributing](#contributing)

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- (Optional) `.env` file with API keys (copy from `.env.example`)

### Deploy

bash
# Clone the repo
git clone https://github.com/Appel420/Sovereignty-AI-Studio.git
cd Sovereignty-AI-Studio

# Copy and configure environment
cp .env.example .env
# Edit .env — set JWT_SECRET, API keys as needed

# Start all services
docker compose up -d

# Apply database schema (auto-applied on first start)
# Health check:
curl http://localhost:9898/health

**Services started:**
| Service | Port | Notes |
|---------|------|-------|
| node-bridge (API gateway) | `9898` | Only external port |
| backend (FastAPI) | internal | Internal Docker only |
| PostgreSQL 16 | internal | Auto-initialized with schema |
| Redis 7 | internal | Session + cache store |

**Production with Nginx reverse proxy:**
bash
docker compose --profile production up -d


---

## Architecture Overview


[Client Browser / API Consumer]
         │
         ▼
  [Nginx :80] ──────────────────────────── (production profile)
         │
         ▼
  [Node Bridge :9898] ─── WebSocket + HTTP gateway
         │
    ┌────┴────┐
    ▼         ▼
[FastAPI :9898]   [Agent Worker]
    │
  ┌─┴──────────────┐
  ▼                ▼
[PostgreSQL]    [Redis]

[AI Provider Router]
  ├── GPT (OpenAI)
  ├── Anthropic (Claude)
  └── Local (self-hosted inference)


All traffic enters through **port 9898** only. The backend, database, and Redis are internal Docker services not exposed to the host.

---

## Subsystems

### AI Studio

**Multi-tenant Organization System**
- Orgs → Projects → Members hierarchy
- Role-based access: `owner`, `admin`, `member`, `contributor`, `viewer`
- Context-aware AI calls tagged by org/project

**AI Provider Routing** (`backend/api/router/`)
- Multi-provider with automatic fallback: GPT → Anthropic → Local
- Set preferred provider per request; system cascades on failure
- Usage tracking per user/org/provider in PostgreSQL

**Frontend Views** (`frontend/views/`)
- `org.js` — Organization management UI
- `project.js` — Project management with visibility control

**Security Dashboard** (`frontend/dashboard/`)
- `security.js` — Real-time audit log viewer with action filtering
- `analytics.js` — Token usage, provider breakdown, active users

**Agent Marketplace** (`plugins/marketplace/`)
- Register and discover custom AI agents
- Plugin SDK (`plugins/sdk/plugin-sdk.js`) for building new agents
- Example weather agent included

**Analytics & Audit Trail** (`backend/analytics/`)
- Full immutable audit log for every AI call, login, and permission change
- Token usage tracking by provider and model
- 100-event query window with action/user filtering

### Sovereignty One Hardware

Modular, solar-powered, zero-liquid-discharge water purification system combining:
- **CDI** (Capacitive Deionization) — brackish to seawater desalination
- **MED** (Multi-Effect Distillation) — volume reduction + polishing
- **Plasma ZLD** — zero liquid discharge + mineral extraction

**ESP32-S3 Firmware** (`sovereignty_one/firmware/esp32_hybrid_controller.ino`)
- Autonomous sensor-driven operation (TDS, pH, ORP, temperature, pressure, flow)
- PV power budget-aware mode selection
- Safety interlocks with JSON telemetry over serial
- Anti-scaling automated flush cycles

**Documentation** (`docs/sovereignty_one/`)
- [README](docs/sovereignty_one/README.md) — System overview
- [Build Manual](docs/sovereignty_one/build_manual.md) — Full assembly instructions
- [BOM CDI](docs/sovereignty_one/bom_cdi.md) — $1,850–$2,300
- [BOM MED](docs/sovereignty_one/bom_med.md) — $2,200–$2,800
- [Grant Proposals](docs/sovereignty_one/grant_proposal.md) — Water4All, NSF WIRE, NASA PSTAR
- [Deployment Plan](docs/sovereignty_one/deployment_plan.md) — Site requirements and installation
- [Brine Mining](docs/sovereignty_one/brine_mining.md) — ZLD mineral extraction revenue model
- [ISRU Off-World](docs/sovereignty_one/isru_offworld.md) — Mars, Moon, Europa, Enceladus, Titan

### SDT-Boron Therapy Research

> ⚠️ **Research and educational purposes only.** Not approved for clinical use. See [full disclaimer](docs/sdt_boron_therapy/README.md).

Experimental cancer treatment combining Sonodynamic Therapy with ¹⁰B-enriched compounds for non-nuclear, image-guided tumor destruction.

**Documentation** (`docs/sdt_boron_therapy/`)
- [README](docs/sdt_boron_therapy/README.md) — Overview and disclaimer
- [Delivery](docs/sdt_boron_therapy/delivery.md) — Liposome, microbubble, small molecule delivery
- [Activation](docs/sdt_boron_therapy/activation.md) — Ultrasound parameters and cavitation monitoring
- [Killing Mechanism](docs/sdt_boron_therapy/killing_mechanism.md) — ROS, DNA repair blockade, apoptosis, ICD
- [References](docs/sdt_boron_therapy/references.md) — 14-entry cross-referenced bibliography

---

## API Reference

All requests proxied through `http://localhost:9898`.

### Authentication

Authorization: Bearer <JWT>

JWT signed with `JWT_SECRET` env var.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/org` | List user's organizations |
| `POST` | `/api/org` | Create organization |
| `GET` | `/api/project?orgId=<id>` | List projects in org |
| `POST` | `/api/project` | Create project |
| `POST` | `/api/ai` | Route prompt to AI provider |
| `GET` | `/api/audit?orgId=<id>` | Get audit logs |
| `GET` | `/api/analytics?orgId=<id>` | Get usage analytics |
| `GET` | `/health` | Health check |

### POST /api/ai
json
{
  "prompt": "Summarize this document",
  "orgId": "uuid",
  "projectId": "uuid",
  "provider": "gpt"  // optional: "gpt" | "anthropic" | "local"
}

Response:
json
{
  "result": "...",
  "provider": "gpt"
}


---

## Dashboard Roles

The platform includes a comprehensive role hierarchy across 11 categories (`backend/config/roles.json`):

| Category | Levels | Example Roles |
|----------|--------|---------------|
| EXECUTIVE | L4–L5 | Supreme Commander, CEO, CSO |
| GOVERNMENT & JUDICIAL | L3–L5 | Head of State, Chief Justice, AG |
| LEGAL & JUSTICE | L2–L4 | Senior Judge, Legal Counsel |
| INTELLIGENCE OPERATIONS | L2–L5 | Director, Senior Analyst, Officer |
| DIPLOMACY & FOREIGN AFFAIRS | L2–L4 | Ambassador, Envoy |
| UNITED NATIONS | L3–L5 | Secretary-General, Rapporteur |
| SAFETY & EMERGENCY | L2–L4 | Emergency Director, Safety Officer |
| HEALTH & MEDICAL | L2–L4 | CMO, Medical Advisor |
| PUBLIC HEALTH | L2–L4 | Public Health Director, Epidemiologist |
| TECHNOLOGY & CYBERSECURITY | L1–L5 | CTO, CISO, Engineer, Developer |
| EDUCATION | L1–L4 | Education Officer, Instructor, Student |

---

## Environment Variables

bash
# Core
DATABASE_URL=postgresql://postgres:password@db:5432/creativeflow_db
REDIS_URL=redis://redis:6379
JWT_SECRET=sovereignty-one-secret

# AI Providers (set keys for providers you want to use)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Local inference (self-hosted, no external API needed)
LOCAL_MODEL=llama3
# Endpoint: http://localhost:11434/api/generate (compatible inference server)

# Node Bridge
BACKEND_URL=http://backend:8000
NODE_BRIDGE_PORT=9898
CORS_ORIGIN=http://localhost:9898


---

## Directory Structure


Sovereignty-AI-Studio/
├── backend/
│   ├── api/               # JS API handlers (org, project, ai)
│   │   ├── providers/     # GPT, Anthropic, local inference
│   │   └── router/        # Multi-provider fallback router
│   ├── analytics/         # Usage tracking + audit logging
│   ├── app/               # FastAPI Python backend
│   ├── config/            # roles.json
│   ├── db/                # schema.sql + PostgreSQL connector
│   ├── middleware/         # JWT auth + permission checks
│   └── workers/           # Agent task queue worker
├── frontend/
│   ├── dashboard/         # Security + analytics dashboards
│   ├── src/               # React TypeScript frontend
│   └── views/             # Org + project management views
├── plugins/
│   ├── marketplace/       # Agent registry + example agent
│   └── sdk/               # SovereigntyPlugin base class
├── sovereignty_one/
│   └── firmware/          # ESP32-S3 CDI/MED/Plasma firmware
├── docs/
│   ├── sovereignty_one/   # Water system documentation
│   └── sdt_boron_therapy/ # Biomedical research documentation
├── infra/
│   ├── nginx/             # Nginx reverse proxy config
│   └── deploy_scripts/    # Automated deployment script
├── node-bridge/           # Node.js WebSocket + HTTP gateway
├── docker-compose.yml     # Full service stack
└── .env.example           # Environment variable template


---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `pytest` + `flake8 --select=E9,F63,F7,F82`
4. Submit a pull request

All hardware designs are released under **CERN-OHL-S-2.0**.  
Software is released under the **MIT License**.  
See [LICENSE](LICENSE) and [SECURITY.md](SECURITY.md) for details.
> main
