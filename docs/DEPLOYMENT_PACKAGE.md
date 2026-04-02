# Sovereignty AI 4.2 Deployment Package (v2)

This replaces the legacy `Deployv2.0.py` artifact with a markdown quick reference that matches the files checked into this repository. Use it as a concise map of what is available and how to stand the stack up.

## Included assets
- `docker-compose.yml` - self-hosted stack (PostgreSQL, Redis, backend, node-bridge, gateway, nginx profile for TLS/static assets)
- `start-all.sh` - local orchestrator that starts Redis (if installed), the weather dashboard (`hypercorn weather_dashboard:app`), the Python gateway (`gateway/main.py`), and the Node.js bridge on port 9898
- `ecosystem.config.cjs` - PM2 profiles for backend, gateway, and node-bridge
- `backend/` + `requirements.txt` - FastAPI services (auth, orgs, media, voice, telemetry) and tests under `tests/`
- `node-bridge/` - WebSocket/HTTP bridge on port 9898 (proxies to gateway and backend)
- `gateway/` - Python multi-agent gateway (`gateway/main.py`) used by node-bridge
- `scripts/` - deployment helpers (`deploy.sh`), database init (`init_db.py`), certificate tooling (`generate-certs.sh`, `tls_rotate.*`), and supporting utilities
- `apps/dashboards/SGHv119.html` and other dashboard artifacts for monitoring agents
- `docs/REPOSITORY_ORGANIZATION.md`, `docs/QUICK_REFERENCE.md`, and related documents for structure and troubleshooting

## Quick start (local)
1) Create a virtual environment and install Python dependencies:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2) Install Node dependencies for the unified server and node-bridge:
```
npm install
(cd node-bridge && npm install)
```
3) Initialize the database schema (uses `db/schema.sql` mounts for Docker; run locally for bare-metal):
```
PYTHONPATH=.:./backend python scripts/init_db.py
```
4) Start services locally:
```
# Option A: process manager
pm2 start ecosystem.config.cjs

# Option B: helper script (Redis + weather dashboard + gateway + node-bridge)
./start-all.sh
```
Health probes:
- Bridge: http://localhost:9898/health
- Gateway: http://localhost:9000/health
- Agents status: http://localhost:9898/api/agents/status

## Containerized deployment
```
docker compose up -d                 # default stack
docker compose --profile production up -d  # enable nginx/TLS profile
```
TLS certificates can be generated locally with `scripts/generate-certs.sh` (self-signed) and mounted via the nginx profile.

## Kubernetes (bring-your-own manifests)
Provide your manifests and apply them, e.g.:
```
kubectl apply -f <path-to-your-k8s-manifests>
```
Expose port 9898 externally; backend, Redis, and Postgres stay on the cluster network.

## Verification checklist
- `PYTHONPATH=.:./backend python -m pytest --strict-markers --tb=short`
- `flake8 --count --select=E9,F63,F7,F82 --show-source --statistics`
- `curl http://localhost:9898/health` (bridge) and `/api/agents/status`
- If running containers: `docker compose ps` shows backend, node-bridge, gateway, db, and redis healthy

## Notes about omitted assets
Scripts and dashboards referenced in earlier drafts (for example `scripts/forge.sh`, `scripts/check_imports.py`, `SuperGrok_Enterprise.html`, or `SuperGrokSingleFile.jsx`) are not present in this repository. Add them separately if needed and update this guide accordingly.
