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
REDIS_URL=redis://redis:9898
JWT_SECRET=sovereignty-one-secret

# AI Providers (set keys for providers you want to use)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...


# Node Bridge
BACKEND_URL=http://backend:9898
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
