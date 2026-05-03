#!/bin/bash
# ═══════════════════════════════════════════════════════
# SOVEREIGNTY AI STUDIO — STARTUP
# Starts both services needed by KODER (frontend on 9898):
#   1. Python AI backend (bridge.py) on port 9897
#   2. Node bridge proxy on port 9898  ← KODER connects here
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

echo "Starting node-bridge proxy on port 9898 (KODER frontend entry point)..."
SG_BRIDGE_URL=ws://localhost:9897 NODE_BRIDGE_PORT=9898 node "$NODE_BRIDGE_DIR/server.js" &
NODE_PID=$!

# Ensure both services are stopped on exit (Ctrl+C or crash)
trap 'echo "Stopping services..."; kill "$BRIDGE_PID" "$NODE_PID" 2>/dev/null' EXIT INT TERM

echo ""
echo "Services running:"
echo "  bridge.py   PID=$BRIDGE_PID  → ws://localhost:9897 (Python AI backend)"
echo "  node-bridge PID=$NODE_PID    → ws://localhost:9898 (KODER connects here)"
echo ""
echo "Open KODER at: http://127.0.0.1:9898"
echo "Press Ctrl+C to stop both services."

# Wait for all background jobs
wait
