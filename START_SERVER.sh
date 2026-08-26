#!/usr/bin/env bash
set -Eeuo pipefail

# Sovereignty AI Studio — canonical local launcher.
# Local-only startup. HTTPS/WSS are runtime requirements for secure transport;
# this launcher does not silently downgrade a secure deployment to HTTP/WSS.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$SCRIPT_DIR/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-node}"
PY_PORT="${SG_PORT:-9897}"
NODE_PORT="${NODE_BRIDGE_PORT:-9899}"
STATIC_PORT="${STATIC_PORT:-9898}"
NETWORK_MODE="${SG_NETWORK_MODE:-offline}"
DEVICE_MODE="${SG_DEVICE_MODE:-ghost}"

case "$DEVICE_MODE" in
  ghost) NETWORK_MODE=offline ;;
  hybrid|online) : ;;
  *) echo "ERROR: unsupported SG_DEVICE_MODE=$DEVICE_MODE" >&2; exit 64 ;;
esac
case "$NETWORK_MODE" in
  offline|hybrid|online) : ;;
  *) echo "ERROR: unsupported SG_NETWORK_MODE=$NETWORK_MODE" >&2; exit 64 ;;
esac

[[ -x "$PYTHON_BIN" ]] || { echo "ERROR: missing local Python runtime: $PYTHON_BIN" >&2; exit 1; }
[[ -f "$SCRIPT_DIR/bridge.py" ]] || { echo "ERROR: missing bridge.py" >&2; exit 1; }
[[ -f "$SCRIPT_DIR/node-bridge/server.js" ]] || { echo "ERROR: missing node-bridge/server.js" >&2; exit 1; }
[[ -d "$SCRIPT_DIR/node-bridge/node_modules" ]] || { echo "ERROR: missing Node dependencies; run ./INSTALL.sh" >&2; exit 1; }
"$PYTHON_BIN" -c 'import websockets' >/dev/null 2>&1 || { echo "ERROR: Python bridge dependencies are missing; run ./INSTALL.sh" >&2; exit 1; }

for port in "$PY_PORT" "$NODE_PORT" "$STATIC_PORT"; do
  if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$port" -sTCP:LISTEN -n >/dev/null 2>&1; then
    echo "ERROR: port $port is already in use; refusing partial startup" >&2
    exit 1
  fi
done

export SG_DEVICE_MODE="$DEVICE_MODE"
export SG_NETWORK_MODE="$NETWORK_MODE"
export SG_ENABLE_REMOTE_NETWORK="${SG_ENABLE_REMOTE_NETWORK:-0}"
export SG_ALLOW_BACKGROUND_POLLING="${SG_ALLOW_BACKGROUND_POLLING:-0}"
export SG_ENABLE_WEBSOCKET="${SG_ENABLE_WEBSOCKET:-0}"
export SG_ENABLE_SSE="${SG_ENABLE_SSE:-0}"
export SG_RUNTIME_OWNER="SGHv119.html"
export SG_HOST="127.0.0.1"
export NODE_BRIDGE_HOST="127.0.0.1"
export PIPER_MODEL="${PIPER_MODEL:-$SCRIPT_DIR/models/en_US-lessac-medium.onnx}"
export PIPER_DIR="${PIPER_DIR:-$SCRIPT_DIR/piper-tts}"

# Do not advertise HTTP as a secure runtime. A TLS-enabled deployment must
# provide explicit certificates and use its HTTPS/WSS entrypoint.
if [[ -n "${TLS_CERT:-}" || -n "${TLS_KEY:-}" ]]; then
  [[ -n "${TLS_CERT:-}" && -n "${TLS_KEY:-}" ]] || { echo "ERROR: TLS_CERT and TLS_KEY must be provided together" >&2; exit 64; }
  [[ -r "$TLS_CERT" && -r "$TLS_KEY" ]] || { echo "ERROR: TLS certificate/key are not readable" >&2; exit 1; }
fi

pids=()
cleanup() {
  trap - EXIT INT TERM
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]:-}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

cd "$SCRIPT_DIR"

SG_PORT="$PY_PORT" SG_HOST=127.0.0.1 SG_NETWORK_MODE="$NETWORK_MODE" SG_DEVICE_MODE="$DEVICE_MODE" \
  "$PYTHON_BIN" bridge.py &
pids+=("$!")

NODE_BRIDGE_PORT="$NODE_PORT" NODE_BRIDGE_HOST=127.0.0.1 \
SG_BRIDGE_HTTP_URL="http://127.0.0.1:$PY_PORT" \
CORS_ORIGIN="${CORS_ORIGIN:-http://127.0.0.1:$STATIC_PORT}" \
SG_NETWORK_MODE="$NETWORK_MODE" SG_DEVICE_MODE="$DEVICE_MODE" \
  "$NODE_BIN" node-bridge/server.js &
pids+=("$!")

"$PYTHON_BIN" -m http.server "$STATIC_PORT" --bind 127.0.0.1 --directory "$SCRIPT_DIR" &
pids+=("$!")

cat <<EOF
Sovereignty AI Studio local runtime started.
  dashboard: http://127.0.0.1:$STATIC_PORT/SGHv119.html (loopback development transport)
  python:    http://127.0.0.1:$PY_PORT
  node:      http://127.0.0.1:$NODE_PORT
  mode:      $DEVICE_MODE / $NETWORK_MODE
EOF

wait -n "${pids[@]}"
status=$?
exit "$status"
