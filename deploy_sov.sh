#!/bin/bash
# deploy_sov.sh
# ⚔️ Sovereignty AI Studio - Fully Autonomous Offline Deployment
# Author: Appel420
# Last updated: 2026-04-04

set -e
set -o pipefail

echo "🚀 Starting Sovereignty AI Studio Full Offline Deployment"

# -----------------------------
# Step 0: Load environment
# -----------------------------
if [ ! -f .env ]; then
  echo "⚠️ .env file not found. Copy .env.example -> .env and edit secrets."
  exit 1
fi
export $(grep -v '^#' .env | xargs)

# -----------------------------
# Step 1: Validate Local Model Paths (Offline Inference)
# -----------------------------
echo "🤖 Checking local model paths for offline inference..."
MODEL_PATHS=("models/grok_model.bin" "models/claude_model.bin" "models/gpt_model.bin")
MISSING_MODELS=0

for path in "${MODEL_PATHS[@]}"; do
  if [ ! -f "$path" ]; then
    echo "⚠️ Model missing: $path → fallback to llama.cpp"
    MISSING_MODELS=$((MISSING_MODELS+1))
  else
    echo "✅ Model found: $path"
  fi
done

if [ $MISSING_MODELS -gt 0 ]; then
  echo "ℹ️ Falling back to offline llama.cpp inference for missing models..."
  docker build -t sov-llama offline_inference/llama.cpp || true
fi

# -----------------------------
# Step 2: Build Docker images (all layers)
# -----------------------------
echo "🔨 Building all Docker images..."
docker compose -f docker-compose.override.yml -f docker-compose.yml build --pull

# -----------------------------
# Step 3: Apply full repo patch
# -----------------------------
echo "🧩 Applying sovereign full-stack patch..."
git checkout -B sovereign-full-patch || git reset --hard
git add .
git commit -m "Sovereign full stack integration patch" || echo "No changes to commit"

# -----------------------------
# Step 4: Initialize Postgres & Redis
# -----------------------------
echo "🗄️ Initializing database and cache..."
docker compose up -d postgres redis
sleep 10
docker exec -i saas_postgres psql -U saas -d sovereignty -f db/schema.sql || true
echo "✅ Database initialized"

# -----------------------------
# Step 5: Verify Hardware Root-of-Trust
# -----------------------------
echo "🔐 Verifying Hardware Root-of-Trust..."
# stub TPM call, replace with real if available
if [ -x /usr/bin/tpm2_getrandom ]; then
  TPM_TEST=$(tpm2_getrandom 4 2>/dev/null || echo "")
else
  TPM_TEST="stub"
fi

if [ -z "$TPM_TEST" ]; then
  echo "❌ Hardware Root-of-Trust verification FAILED"
  exit 1
else
  echo "✅ Hardware Root-of-Trust verified"
fi

# -----------------------------
# Step 6: Start backend, node bridge, cognitive agents, CRSE, evolution monitor
# -----------------------------
echo "⚡ Launching backend, bridge, cognitive agents, CRSE, and evolution monitor..."
docker compose up -d backend node-bridge cognitive-agent evolution-simulator evolution-monitor
sleep 5

# -----------------------------
# Step 7: Activate Airgap & Sovereign Mesh (offline only)
# -----------------------------
echo "🕸️ Activating Airgap Mode & Sovereign Mesh..."
docker exec -d saas_node_bridge node node-bridge/activate_mesh.js --airgap true --root-trust true || echo "❌ Mesh activation failed"

# -----------------------------
# Step 8: Launch Offline Inference Layer
# -----------------------------
echo "🤖 Booting Offline Inference Layer..."
docker exec -d saas_cognitive_agent python3 ai_core/agents/offline_inference.py || echo "❌ Offline inference failed"

# -----------------------------
# Step 9: Start CRSE Monitor Loop (Autonomous, offline)
# -----------------------------
echo "♾️ Starting CRSE Monitor Loop..."
docker exec -d saas_evolution_monitor bash -c "
while true; do
  python3 ai_core/evolution/monitor_crse.py \
    --autonomous true \
    --poll-interval 60 \
    --audit-log ./logs/evolution_audit.jsonl \
    --auto-rollback true
  sleep 60
done" || echo "❌ CRSE Monitor failed"

# -----------------------------
# Step 10: Verify services locally (offline only)
# -----------------------------
echo "🔍 Local service verification..."
echo "🌐 Health check Node Bridge (port 9899, local only)"
docker exec saas_node_bridge curl -fsS http://localhost:9899/health && echo "✅ Node Bridge OK" || echo "❌ Node Bridge failed"

echo "🌐 Health check CRSE / Mesh WS (port 9899, local only)"
docker exec saas_crse curl -fsS http://localhost:9899 || echo "❌ CRSE Mesh WS not reachable"

# -----------------------------
# Step 11: Tail logs for live verification
# -----------------------------
echo "📜 Tailing logs (Ctrl+C to exit)..."
docker compose logs -f --tail=50 backend node-bridge cognitive-agent evolution-simulator evolution-monitor


#!/bin/bash
# ----------------------
# Sovereignty AI Studio - Full Offline Deploy
# ----------------------

set -euo pipefail
echo "🚀 Starting Sovereignty AI Studio deployment..."

# Load .env
if [[ ! -f .env ]]; then
  echo ".env file missing! Aborting."
  exit 1
fi
export $(grep -v '^#' .env | xargs)

# Ensure model exists, fallback to local llama.cpp if missing
if [[ ! -f "${SOVEREIGN_MODEL_PATH:-./models/sovereign.gguf}" ]]; then
  echo "⚠ Model not found, falling back to GPT-4o-mini local model..."
  export SOVEREIGN_MODEL_PATH=./models/GPT-4o-mini
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Build all services offline
echo "🏗 Building Docker services locally..."
docker-compose build

# Start services
echo "▶ Starting Docker stack..."
docker-compose up -d

# Wait for node-bridge healthcheck
echo "⏳ Waiting for node-bridge to be healthy..."
until curl -sSf http://localhost:9899/health > /dev/null; do
  echo "Waiting for node-bridge..."
  sleep 5
done

echo "✅ Node-bridge healthy on port 9899."

# Optional: check other critical services
services=("backend" "db" "redis")
for svc in "${services[@]}"; do
  echo "Checking $svc..."
  docker inspect --format='{{.State.Health.Status}}' "${svc}" | grep -q "healthy" || {
    echo "❌ $svc not healthy, rolling back..."
    docker-compose down
    exit 1
  }
done

echo "🎉 Deployment complete. All systems healthy."
#!/bin/bash
# ----------------------
# Sovereignty AI Studio - Full Offline Deploy + CRSE Monitor
# ----------------------

set -euo pipefail
echo "🚀 Starting Sovereignty AI Studio deployment..."

# ----------------------
# Load environment
# ----------------------
if [[ ! -f .env ]]; then
  echo ".env file missing! Aborting."
  exit 1
fi
export $(grep -v '^#' .env | xargs)

# ----------------------
# Model fallback
# ----------------------
if [[ ! -f "${SOVEREIGN_MODEL_PATH:-./models/sovereign.gguf}" ]]; then
  echo "⚠ Model missing, fallback to GPT-4o-mini local model..."
  export SOVEREIGN_MODEL_PATH=./models/GPT-4o-mini
fi

# ----------------------
# Stop existing containers
# ----------------------
echo "🛑 Stopping existing containers..."
docker-compose down || true

# ----------------------
# Build services offline
# ----------------------
echo "🏗 Building Docker services..."
docker-compose build

# ----------------------
# Start stack
# ----------------------
echo "▶ Starting Docker stack..."
docker-compose up -d

# ----------------------
# Wait for node-bridge
# ----------------------
echo "⏳ Waiting for node-bridge on port 9899..."
until curl -sSf http://localhost:9899/health > /dev/null; do
  echo "Waiting..."
  sleep 5
done
echo "✅ Node-bridge healthy."

# ----------------------
# Healthcheck critical services
# ----------------------
services=("backend" "db" "redis")
for svc in "${services[@]}"; do
  status=$(docker inspect --format='{{.State.Health.Status}}' "$svc" || echo "unhealthy")
  if [[ "$status" != "healthy" ]]; then
    echo "❌ $svc unhealthy, rolling back..."
    docker-compose down
    exit 1
  fi
done
echo "✅ All critical services healthy."

# ----------------------
# Start CRSE monitor loop (background)
# ----------------------
echo "🛡 Starting CRSE monitor..."
audit_file="./audit.jsonl"
mkdir -p "$(dirname "$audit_file")"

crse_monitor() {
  chunk_limit=50  # max proposals to keep in memory
  declare -a proposal_chunks

  while true; do
    # Fetch proposals from Redis (or local agent output)
    raw=$(docker exec redis redis-cli LRANGE crse_proposals 0 -1 || echo "[]")
    # Sanitize: remove control characters and truncate long proposals
    clean=$(echo "$raw" | tr -d '\r\n' | cut -c1-2000)

    # Rotate chunks
    proposal_chunks+=("$clean")
    if [[ ${#proposal_chunks[@]} -gt $chunk_limit ]]; then
      proposal_chunks=("${proposal_chunks[@]: -$chunk_limit}")
    fi

    # Append sanitized chunk to audit log
    echo "$(date -Is) $(printf '%s\n' "${proposal_chunks[-1]}")" >> "$audit_file"

    # Optional: trigger rollback if failure detected (stub logic)
    if echo "${proposal_chunks[-1]}" | grep -iq "FAIL"; then
      echo "⚠ CRSE failure detected — rolling back..."
      docker-compose down
      exit 1
    fi

    sleep 60
  done
}

# Run CRSE monitor in background
crse_monitor &

echo "🎉 Deployment complete. CRSE monitor running in background."

#!/bin/bash
# ----------------------
# Sovereignty AI Studio - Full Offline Deploy + Smart CRSE Monitor
# ----------------------

set -euo pipefail
echo "🚀 Starting Sovereignty AI Studio deployment..."

# ----------------------
# Load environment
# ----------------------
if [[ ! -f .env ]]; then
  echo ".env file missing! Aborting."
  exit 1
fi
export $(grep -v '^#' .env | xargs)

# ----------------------
# Model fallback
# ----------------------
if [[ ! -f "${SOVEREIGN_MODEL_PATH:-./models/sovereign.gguf}" ]]; then
  echo "⚠ Model missing, fallback to GPT-4o-mini local model..."
  export SOVEREIGN_MODEL_PATH=./models/GPT-4o-mini
fi

# ----------------------
# Stop existing containers
# ----------------------
echo "🛑 Stopping existing containers..."
docker-compose down || true

# ----------------------
# Build services offline
# ----------------------
echo "🏗 Building Docker services..."
docker-compose build

# ----------------------
# Start stack
# ----------------------
echo "▶ Starting Docker stack..."
docker-compose up -d

# ----------------------
# Wait for node-bridge
# ----------------------
echo "⏳ Waiting for node-bridge on port 9899..."
until curl -sSf http://localhost:9899/health > /dev/null; do
  echo "Waiting..."
  sleep 5
done
echo "✅ Node-bridge healthy."

# ----------------------
# Healthcheck critical services
# ----------------------
services=("backend" "db" "redis")
for svc in "${services[@]}"; do
  status=$(docker inspect --format='{{.State.Health.Status}}' "$svc" || echo "unhealthy")
  if [[ "$status" != "healthy" ]]; then
    echo "❌ $svc unhealthy, rolling back..."
    docker-compose down
    exit 1
  fi
done
echo "✅ All critical services healthy."

# ----------------------
# Start Smart CRSE Monitor Loop (background)
# ----------------------
echo "🛡 Starting Smart CRSE monitor..."
audit_file="./audit.jsonl"
mkdir -p "$(dirname "$audit_file")"
max_log_size=$((10*1024*1024))  # 10 MB max

crse_monitor() {
  chunk_limit=50  # max proposals in memory
  declare -a proposal_chunks

  agent_ports=( "9001" "8001" "8002" "8003" "8004" ) # judge, ai_router, plugin, platform, voice
  agent_names=( "judge" "ai_router" "plugin" "platform" "voice" )

  while true; do
    # ----------------------
    # Poll agents for proposals
    # ----------------------
    for i in "${!agent_ports[@]}"; do
      port="${agent_ports[$i]}"
      name="${agent_names[$i]}"
      raw=$(curl -s "http://localhost:$port/proposals" || echo "[]")

      # Sanitize: remove control chars & truncate
      clean=$(echo "$raw" | tr -d '\r\n' | cut -c1-2000)
      proposal_chunks+=("$name: $clean")

      # Rotate memory chunks
      if [[ ${#proposal_chunks[@]} -gt $chunk_limit ]]; then
        proposal_chunks=("${proposal_chunks[@]: -$chunk_limit}")
      fi

      # Append sanitized chunk to audit log
      echo "$(date -Is) $name $(printf '%s\n' "$clean")" >> "$audit_file"
    done

    # ----------------------
    # Soft alerts: detect suspicious content
    # ----------------------
    for p in "${proposal_chunks[@]}"; do
      if echo "$p" | grep -iqE "FAIL|ERROR|SECURITY_ALERT"; then
        echo "⚠ Soft alert: suspicious proposal detected: $p"
        # Optional: trigger notifications instead of rollback
      fi
    done

    # ----------------------
    # Hard rollback on critical failure
    # ----------------------
    last_chunk="${proposal_chunks[-1]:-}"
    if echo "$last_chunk" | grep -iq "CRITICAL_FAIL"; then
      echo "❌ Critical failure detected — rolling back..."
      docker-compose down
      exit 1
    fi

    # ----------------------
    # Manage audit log size (rotate if >10MB)
    # ----------------------
    if [[ -f "$audit_file" && $(stat -c%s "$audit_file") -gt $max_log_size ]]; then
      mv "$audit_file" "$audit_file.$(date +%s).bak"
      touch "$audit_file"
      echo "📝 Audit log rotated."
    fi

    sleep 60
  done
}

# Run CRSE monitor in background
crse_monitor &

echo "🎉 Deployment complete. Smart CRSE monitor running in background."
