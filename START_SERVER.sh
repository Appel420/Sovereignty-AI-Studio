#!/bin/bash
# ═══════════════════════════════════════════════════════
# SOVEREIGNTY AI STUDIO — STARTUP
# Port architecture:
#   9898 — KODER frontend (SGHv119.html static file server)
#   9897 — Python AI backend (bridge.py WebSocket server)
#   9899 — Node bridge proxy (server.js — WS/API proxy)
# Zero Meta · Zero Google · Zero LLaMA · Zero Ollama
# All AI: DDG Privacy Bridge + Piper TTS (local only)
# ═══════════════════════════════════════════════════════

# Set your Piper model path (download from github.com/rhasspy/piper/releases)
export PIPER_MODEL="${PIPER_MODEL:-./models/en_US-lessac-medium.onnx}"
export PIPER_DIR="${PIPER_DIR:-./piper-tts}"

# Optional: your self-signed TLS cert
export TLS_CERT="${TLS_CERT:-}"
export TLS_KEY="${TLS_KEY:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_BRIDGE_DIR="$SCRIPT_DIR/node-bridge"

if [ ! -f "$NODE_BRIDGE_DIR/server.js" ]; then
  echo "ERROR: node-bridge/server.js not found at $NODE_BRIDGE_DIR" >&2
  exit 1
fi

echo "Starting Python AI backend (bridge.py) on port 9897..."
echo "Piper model: $PIPER_MODEL"
echo "Network: localhost only — nothing leaves device without user permission"
echo ""

# Start Python backend in background
SG_PORT=9897 python bridge.py &
BRIDGE_PID=$!

echo "Starting node-bridge proxy on port 9899..."
SG_BRIDGE_URL=ws://127.0.0.1:9897 NODE_BRIDGE_PORT=9899 node "$NODE_BRIDGE_DIR/server.js" &
NODE_PID=$!

echo "Starting KODER frontend static server on port 9898..."
# Serve SGHv119.html at http://127.0.0.1:9898 — python3 is always available
python3 -m http.server 9898 --bind 127.0.0.1 --directory "$SCRIPT_DIR" &
STATIC_PID=$!

# Ensure all services are stopped on exit (Ctrl+C or crash)
trap 'echo "Stopping services..."; kill "$BRIDGE_PID" "$NODE_PID" "$STATIC_PID" 2>/dev/null' EXIT INT TERM

echo ""
echo "Services running:"
echo "  bridge.py   PID=$BRIDGE_PID   → ws://127.0.0.1:9897  (Python AI backend)"
echo "  node-bridge PID=$NODE_PID     → ws://127.0.0.1:9899  (node bridge proxy)"
echo "  static srv  PID=$STATIC_PID  → http://localhost:9898 (KODER frontend)"
echo ""
echo "Open KODER at: http://localhost:9898/SGHv119.html"
echo "Press Ctrl+C to stop all services."

# Wait for all background jobs
wait
