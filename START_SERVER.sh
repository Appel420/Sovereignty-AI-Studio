        feature/canonical-governance-core
#!/usr/bin/env bash
# Sovereignty AI Studio — canonical local launcher.
# One launcher, one port map, loopback only, no cloud services.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-node}"
PY_PORT="${SG_PORT:-9897}"
NODE_PORT="${NODE_BRIDGE_PORT:-9899}"
STATIC_PORT="${STATIC_PORT:-9898}"
NETWORK_MODE="${SG_NETWORK_MODE:-local}"

if [[ "$NETWORK_MODE" != "local" && "$NETWORK_MODE" != "offline" ]]; then
  echo "Refusing startup: SG_NETWORK_MODE must be local or offline (got $NETWORK_MODE)." >&2
  exit 1
fi

[[ -x "$PYTHON_BIN" ]] || { echo "Missing local Python runtime: $PYTHON_BIN. Run ./INSTALL.sh first." >&2; exit 1; }
[[ -f "$ROOT_DIR/bridge.py" ]] || { echo "Missing bridge.py." >&2; exit 1; }
[[ -f "$ROOT_DIR/node-bridge/server.js" ]] || { echo "Missing node-bridge/server.js." >&2; exit 1; }
[[ -d "$ROOT_DIR/node-bridge/node_modules" ]] || { echo "Missing Node dependencies. Run npm ci in node-bridge." >&2; exit 1; }

for port in "$PY_PORT" "$NODE_PORT" "$STATIC_PORT"; do
  if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$port" -sTCP:LISTEN -n >/dev/null 2>&1; then
    echo "Port $port is already in use; refusing partial startup." >&2
    exit 1
  fi
done

export PIPER_MODEL="${PIPER_MODEL:-$ROOT_DIR/models/en_US-lessac-medium.onnx}"
export SG_NETWORK_MODE="$NETWORK_MODE"
export SG_HOST="127.0.0.1"
export NODE_BRIDGE_HOST="127.0.0.1"
export CORS_ORIGIN="${CORS_ORIGIN:-http://127.0.0.1:$STATIC_PORT}"
pids=()
cleanup() {
  trap - EXIT INT TERM
  echo "Stopping local services..."
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]:-}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

SG_PORT="$PY_PORT" "$PYTHON_BIN" "$ROOT_DIR/bridge.py" &
pids+=("$!")

NODE_BRIDGE_PORT="$NODE_PORT" \
SG_BRIDGE_HTTP_URL="http://127.0.0.1:$PY_PORT" \
CORS_ORIGIN="$CORS_ORIGIN" \
SG_NETWORK_MODE="$NETWORK_MODE" \
"$NODE_BIN" "$ROOT_DIR/node-bridge/server.js" &
pids+=("$!")

"$PYTHON_BIN" -m http.server "$STATIC_PORT" --bind 127.0.0.1 --directory "$ROOT_DIR" &
pids+=("$!")

echo "Local services running:"
echo "  dashboard: http://127.0.0.1:$STATIC_PORT/SGHv119.html"
echo "  Python:    http://127.0.0.1:$PY_PORT"
echo "  Node:      http://127.0.0.1:$NODE_PORT"
echo "  mode:      $NETWORK_MODE"
echo "Press Ctrl+C to stop."

wait -n "${pids[@]}"
exit $?

#!/bin/bash
set -Eeuo pipefail
# ═══════════════════════════════════════════════════════
# SOVEREIGNTY AI STUDIO — CANONICAL LOCAL STARTUP
#   9898 — SGHv119.html static dashboard
#   9897 — Python bridge
#   9899 — Node bridge/API proxy
#
# The root launcher is the only supported local runtime entry point.
# External, Docker, PM2, and legacy launchers are not started here.
# ═══════════════════════════════════════════════════════

export SG_DEVICE_MODE="${SG_DEVICE_MODE:-ghost}"
export SG_NETWORK_MODE="${SG_NETWORK_MODE:-offline}"
export SG_ENABLE_REMOTE_NETWORK="${SG_ENABLE_REMOTE_NETWORK:-0}"
export SG_ALLOW_BACKGROUND_POLLING="${SG_ALLOW_BACKGROUND_POLLING:-0}"
export SG_ENABLE_WEBSOCKET="${SG_ENABLE_WEBSOCKET:-0}"
export SG_ENABLE_SSE="${SG_ENABLE_SSE:-0}"
export SG_RUNTIME_OWNER="SGHv119.html"

case "$SG_DEVICE_MODE" in
  ghost)
    # Ghost is the device-level high-assurance mode. The existing bridge
    # network policy uses "offline" for the same transport boundary.
    SG_NETWORK_MODE=offline
    SG_ENABLE_REMOTE_NETWORK=0
    SG_ALLOW_BACKGROUND_POLLING=0
    SG_ENABLE_WEBSOCKET=0
    SG_ENABLE_SSE=0
    export SG_NETWORK_MODE SG_ENABLE_REMOTE_NETWORK SG_ALLOW_BACKGROUND_POLLING SG_ENABLE_WEBSOCKET SG_ENABLE_SSE
    ;;
  hybrid|online)
    ;;
  *)
    echo "ERROR: unsupported SG_DEVICE_MODE=$SG_DEVICE_MODE" >&2
    echo "Allowed modes: ghost, hybrid, online" >&2
    exit 1
    ;;
esac

case "$SG_NETWORK_MODE" in
  offline|hybrid|online) ;;
  *)
    echo "ERROR: unsupported SG_NETWORK_MODE=$SG_NETWORK_MODE" >&2
    exit 1
    ;;
esac

export PIPER_MODEL="${PIPER_MODEL:-./models/en_US-lessac-medium.onnx}"
export PIPER_DIR="${PIPER_DIR:-./piper-tts}"
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
if ! "$PYTHON_BIN" -c "import websockets" >/dev/null 2>&1; then
  echo "ERROR: Python bridge dependencies are missing. Run ./INSTALL.sh first." >&2
  exit 1
fi

cd "$SCRIPT_DIR"
echo "Starting canonical Sovereignty AI Studio runtime..."
echo "Runtime owner: $SG_RUNTIME_OWNER"
echo "Device mode: $SG_DEVICE_MODE"
echo "Network policy: $SG_NETWORK_MODE"
echo "Background polling: $SG_ALLOW_BACKGROUND_POLLING"
echo "WebSocket capability: $SG_ENABLE_WEBSOCKET"
echo "SSE capability: $SG_ENABLE_SSE"
echo "Remote network: $SG_ENABLE_REMOTE_NETWORK"
echo ""

SG_PORT=9897 \
SG_HOST=127.0.0.1 \
SG_NETWORK_MODE="$SG_NETWORK_MODE" \
SG_DEVICE_MODE="$SG_DEVICE_MODE" \
SG_ALLOW_BACKGROUND_POLLING="$SG_ALLOW_BACKGROUND_POLLING" \
SG_ENABLE_WEBSOCKET="$SG_ENABLE_WEBSOCKET" \
SG_ENABLE_SSE="$SG_ENABLE_SSE" \
SG_ENABLE_REMOTE_NETWORK="$SG_ENABLE_REMOTE_NETWORK" \
"$PYTHON_BIN" bridge.py &
BRIDGE_PID=$!

NODE_BRIDGE_PORT=9899 \
NODE_BRIDGE_HOST=127.0.0.1 \
SG_BRIDGE_URL="${SG_BRIDGE_URL:-}" \
SG_BRIDGE_HTTP_URL="${SG_BRIDGE_HTTP_URL:-http://127.0.0.1:9897}" \
CORS_ORIGIN="${CORS_ORIGIN:-http://127.0.0.1:9898}" \
SG_NETWORK_MODE="$SG_NETWORK_MODE" \
SG_DEVICE_MODE="$SG_DEVICE_MODE" \
SG_ALLOW_BACKGROUND_POLLING="$SG_ALLOW_BACKGROUND_POLLING" \
SG_ENABLE_WEBSOCKET="$SG_ENABLE_WEBSOCKET" \
SG_ENABLE_SSE="$SG_ENABLE_SSE" \
SG_ENABLE_REMOTE_NETWORK="$SG_ENABLE_REMOTE_NETWORK" \
node "$NODE_BRIDGE_DIR/server.js" &
NODE_PID=$!

"$PYTHON_BIN" -m http.server 9898 --bind 127.0.0.1 --directory "$SCRIPT_DIR" &
STATIC_PID=$!

cleanup() {
  echo "Stopping canonical services..."
  kill "$BRIDGE_PID" "$NODE_PID" "$STATIC_PID" 2>/dev/null || true
  wait "$BRIDGE_PID" "$NODE_PID" "$STATIC_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cat <<EOF
Services running:
  dashboard  PID=$STATIC_PID  -> http://127.0.0.1:9898/SGHv119.html
  python     PID=$BRIDGE_PID  -> http://127.0.0.1:9897 (WebSocket backend capability)
  node       PID=$NODE_PID    -> http://127.0.0.1:9899 (HTTP/API bridge)
  mode       $SG_DEVICE_MODE / $SG_NETWORK_MODE
EOF

echo "Press Ctrl+C to stop all services."
wait -n "$BRIDGE_PID" "$NODE_PID" "$STATIC_PID"
status=$?
exit "$status"
        main
