#!/bin/bash
# ═══════════════════════════════════════════════════════
# SOVEREIGNTY AI STUDIO — STARTUP
# Port architecture:
#   9898 — KODER frontend (SGHv119.html static file server)
#   9897 — Python AI backend (bridge.py)
#   9899 — Node bridge proxy (server.js — HTTP/API bridge; optional WS)
# Zero Meta · Zero Google · Zero LLaMA · Zero Ollama
# All AI: DDG Privacy Bridge + Piper TTS (local only)
# ═══════════════════════════════════════════════════════

# Set your Piper model path.
export PIPER_MODEL="${PIPER_MODEL:-./models/en_US-lessac-medium.onnx}"
export PIPER_DIR="${PIPER_DIR:-./piper-tts}"

# Optional: your self-signed TLS cert
export TLS_CERT="${TLS_CERT:-}"
export TLS_KEY="${TLS_KEY:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_BRIDGE_DIR="$SCRIPT_DIR/node-bridge"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$NODE_BRIDGE_DIR/server.js" ]; then
  echo "ERROR: node-bridge/server.js not found at $NODE_BRIDGE_DIR" >&2
  exit 1
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: Local runtime is not installed. Run ./INSTALL.sh first." >&2
  exit 1
fi
if [ ! -d "$NODE_BRIDGE_DIR/node_modules" ]; then
  echo "ERROR: Node bridge dependencies are not installed. Run ./INSTALL.sh first." >&2
  exit 1
fi
if [ -z "${SOVEREIGN_MODEL_PATH:-}" ] || [ ! -f "$SOVEREIGN_MODEL_PATH" ]; then
  echo "ERROR: Set SOVEREIGN_MODEL_PATH to an existing local GGUF model; no model is simulated or downloaded at runtime." >&2
  exit 1
fi
if ! "$PYTHON_BIN" -c "import llama_cpp, websockets" >/dev/null 2>&1; then
  echo "ERROR: Local inference dependencies are missing. Run ./INSTALL.sh first." >&2
  exit 1
fi

echo "Starting Python AI backend (bridge.py) on port 9897..."
echo "Piper model: $PIPER_MODEL"
echo "Network: local-only by default — override with env vars for hosted deployments"
echo ""

# Start Python backend in background
SG_PORT=9897 "$PYTHON_BIN" bridge.py &
BRIDGE_PID=$!

echo "Starting node-bridge proxy on port 9899..."
NODE_BRIDGE_PORT=9899 \
SG_BRIDGE_URL="${SG_BRIDGE_URL:-}" \
SG_BRIDGE_HTTP_URL="${SG_BRIDGE_HTTP_URL:-http://127.0.0.1:9897}" \
CORS_ORIGIN="${CORS_ORIGIN:-http://127.0.0.1:9898}" \
node "$NODE_BRIDGE_DIR/server.js" &
NODE_PID=$!

echo "Starting KODER frontend static server on port 9898..."
# Serve SGHv119.html at http://127.0.0.1:9898 — python3 is always available
"$PYTHON_BIN" -m http.server 9898 --bind 127.0.0.1 --directory "$SCRIPT_DIR" &
STATIC_PID=$!

# Ensure all services are stopped on exit (Ctrl+C or crash)
cleanup() {
  echo "Stopping services..."
  kill "$BRIDGE_PID" "$NODE_PID" "$STATIC_PID" 2>/dev/null || true
  wait "$BRIDGE_PID" "$NODE_PID" "$STATIC_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "Services running:"
echo "  bridge.py   PID=$BRIDGE_PID   → http://127.0.0.1:9897 (Python backend)"
echo "  node-bridge PID=$NODE_PID     → http://127.0.0.1:9899 (HTTP bridge/API proxy)"
echo "  static srv  PID=$STATIC_PID   → http://127.0.0.1:9898 (KODER frontend)"
echo ""
echo "Open KODER at: http://127.0.0.1:9898/SGHv119.html"
echo "Press Ctrl+C to stop all services."

# If any service exits, terminate the remaining services instead of leaving a
# partially functional dashboard running.
wait -n "$BRIDGE_PID" "$NODE_PID" "$STATIC_PID"
status=$?
exit "$status"
