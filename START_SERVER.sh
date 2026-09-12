#!/usr/bin/env bash
# Sovereignty AI Studio — canonical local runtime launcher.
# One launcher, one runtime owner, fail-closed Diamond Core contract gate.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-node}"
PY_PORT="${SG_PORT:-9897}"
NODE_PORT="${NODE_BRIDGE_PORT:-9899}"
STATIC_PORT="${STATIC_PORT:-9898}"
NETWORK_MODE="${SG_NETWORK_MODE:-offline}"

if [[ "$NETWORK_MODE" != "local" && "$NETWORK_MODE" != "offline" ]]; then
  echo "Refusing startup: SG_NETWORK_MODE must be local or offline (got $NETWORK_MODE)." >&2
  exit 1
fi

[[ -x "$PYTHON_BIN" ]] || { echo "Missing local Python runtime: $PYTHON_BIN. Run ./INSTALL.sh first." >&2; exit 1; }
[[ -f "$ROOT_DIR/bridge.py" ]] || { echo "Missing bridge.py." >&2; exit 1; }
[[ -f "$ROOT_DIR/node-bridge/server.js" ]] || { echo "Missing node-bridge/server.js." >&2; exit 1; }
[[ -d "$ROOT_DIR/node-bridge/node_modules" ]] || { echo "Missing Node dependencies. Run npm ci in node-bridge." >&2; exit 1; }

# Diamond Core is an admission gate, not an optional health check.
# No service starts until the pure-software contract passes.
"$ROOT_DIR/scripts/diamond-core-runtime-gate.sh"

for port in "$PY_PORT" "$NODE_PORT" "$STATIC_PORT"; do
  if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$port" -sTCP:LISTEN -n >/dev/null 2>&1; then
    echo "Port $port is already in use; refusing partial startup." >&2
    exit 1
  fi
done

export PIPER_MODEL="${PIPER_MODEL:-$ROOT_DIR/models/en_US-lessac-medium.onnx}"
export PIPER_DIR="${PIPER_DIR:-$ROOT_DIR/piper-tts}"
export SG_NETWORK_MODE="$NETWORK_MODE"
export SG_HOST="127.0.0.1"
export NODE_BRIDGE_HOST="127.0.0.1"
export SG_DEVICE_MODE="${SG_DEVICE_MODE:-ghost}"
export SG_ENABLE_REMOTE_NETWORK="0"
export SG_ALLOW_BACKGROUND_POLLING="0"
export SG_ENABLE_WEBSOCKET="${SG_ENABLE_WEBSOCKET:-0}"
export SG_ENABLE_SSE="${SG_ENABLE_SSE:-0}"
export SG_RUNTIME_OWNER="SGHv119.html"
export CORS_ORIGIN="${CORS_ORIGIN:-http://127.0.0.1:$STATIC_PORT}"

pids=()
cleanup() {
  trap - EXIT INT TERM
  echo "Stopping canonical local services..."
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]:-}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

SG_PORT="$PY_PORT" \
SG_HOST=127.0.0.1 \
SG_NETWORK_MODE="$NETWORK_MODE" \
SG_DEVICE_MODE="$SG_DEVICE_MODE" \
SG_ENABLE_REMOTE_NETWORK="$SG_ENABLE_REMOTE_NETWORK" \
SG_ALLOW_BACKGROUND_POLLING="$SG_ALLOW_BACKGROUND_POLLING" \
SG_ENABLE_WEBSOCKET="$SG_ENABLE_WEBSOCKET" \
SG_ENABLE_SSE="$SG_ENABLE_SSE" \
"$PYTHON_BIN" "$ROOT_DIR/bridge.py" &
pids+=("$!")

NODE_BRIDGE_PORT="$NODE_PORT" \
NODE_BRIDGE_HOST=127.0.0.1 \
SG_BRIDGE_HTTP_URL="http://127.0.0.1:$PY_PORT" \
CORS_ORIGIN="$CORS_ORIGIN" \
SG_NETWORK_MODE="$NETWORK_MODE" \
SG_DEVICE_MODE="$SG_DEVICE_MODE" \
SG_ENABLE_REMOTE_NETWORK="$SG_ENABLE_REMOTE_NETWORK" \
SG_ALLOW_BACKGROUND_POLLING="$SG_ALLOW_BACKGROUND_POLLING" \
SG_ENABLE_WEBSOCKET="$SG_ENABLE_WEBSOCKET" \
SG_ENABLE_SSE="$SG_ENABLE_SSE" \
"$NODE_BIN" "$ROOT_DIR/node-bridge/server.js" &
pids+=("$!")

"$PYTHON_BIN" -m http.server "$STATIC_PORT" --bind 127.0.0.1 --directory "$ROOT_DIR" &
pids+=("$!")

echo "Canonical Sovereignty AI Studio runtime running:"
echo "  dashboard: http://127.0.0.1:$STATIC_PORT/SGHv119.html"
echo "  Python:    http://127.0.0.1:$PY_PORT"
echo "  Node:      http://127.0.0.1:$NODE_PORT"
echo "  mode:      $SG_DEVICE_MODE / $SG_NETWORK_MODE"
echo "  diamond:   PASS (startup admitted)"

echo "Press Ctrl+C to stop."
wait -n "${pids[@]}"
exit $?
