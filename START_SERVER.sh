#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-node}"
PY_PORT="${SG_PORT:-9897}"
NODE_PORT="${NODE_BRIDGE_PORT:-9899}"
STATIC_PORT="${STATIC_PORT:-9898}"
TLS_DIR="${SG_TLS_DIR:-$ROOT_DIR/.tls}"
TLS_CERT="${TLS_CERT:-$TLS_DIR/server.crt}"
TLS_KEY="${TLS_KEY:-$TLS_DIR/server.key}"
NETWORK_MODE="${SG_NETWORK_MODE:-offline}"

case "$NETWORK_MODE" in offline|hybrid|online) ;; *) echo "ERROR: invalid SG_NETWORK_MODE=$NETWORK_MODE" >&2; exit 1 ;; esac

[[ -x "$PYTHON_BIN" ]] || { echo "ERROR: missing Python runtime: $PYTHON_BIN" >&2; exit 1; }
[[ -d "$ROOT_DIR/node-bridge/node_modules" ]] || { echo "ERROR: missing Node dependencies" >&2; exit 1; }
[[ -f "$TLS_CERT" && -f "$TLS_KEY" ]] || {
  echo "ERROR: TLS material missing. Run ./scripts/generate-local-tls.sh first." >&2
  exit 1
}

for port in "$PY_PORT" "$NODE_PORT" "$STATIC_PORT"; do
  if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$port" -sTCP:LISTEN -n >/dev/null 2>&1; then
    echo "ERROR: port $port is already in use; refusing partial startup." >&2
    exit 1
  fi
done

export TLS_CERT TLS_KEY SG_NETWORK_MODE="$NETWORK_MODE"
export SG_HOST="127.0.0.1"
export NODE_BRIDGE_HOST="127.0.0.1"
export CORS_ORIGIN="${CORS_ORIGIN:-https://127.0.0.1:$STATIC_PORT}"
export SG_BRIDGE_URL="${SG_BRIDGE_URL:-wss://127.0.0.1:$PY_PORT}"
export SG_BRIDGE_HTTP_URL="${SG_BRIDGE_HTTP_URL:-https://127.0.0.1:$PY_PORT}"

pids=()
cleanup() {
  trap - EXIT INT TERM
  echo "Stopping Sovereignty services..."
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]:-}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

PYTHONPATH="$ROOT_DIR/bridge:$ROOT_DIR" \
TLS_CERT="$TLS_CERT" TLS_KEY="$TLS_KEY" \
SG_PORT="$PY_PORT" SG_HOST=127.0.0.1 \
"$PYTHON_BIN" "$ROOT_DIR/bridge/secure_server.py" &
pids+=("$!")

TLS_CERT="$TLS_CERT" TLS_KEY="$TLS_KEY" \
NODE_BRIDGE_PORT="$NODE_PORT" NODE_BRIDGE_HOST=127.0.0.1 \
SG_BRIDGE_URL="$SG_BRIDGE_URL" SG_BRIDGE_HTTP_URL="$SG_BRIDGE_HTTP_URL" \
CORS_ORIGIN="$CORS_ORIGIN" SG_NETWORK_MODE="$NETWORK_MODE" \
"$NODE_BIN" "$ROOT_DIR/node-bridge/secure-server.js" &
pids+=("$!")

"$PYTHON_BIN" "$ROOT_DIR/scripts/https_static_server.py" \
  --host 127.0.0.1 --port "$STATIC_PORT" --directory "$ROOT_DIR" \
  --cert "$TLS_CERT" --key "$TLS_KEY" &
pids+=("$!")

cat <<EOF
SOVEREIGNTY AI STUDIO — SECURE RUNTIME
  dashboard: https://127.0.0.1:$STATIC_PORT/SGHv119.html
  python:    wss://127.0.0.1:$PY_PORT
  node:      https://127.0.0.1:$NODE_PORT
  transport: TLS 1.3 / HTTPS / WSS
  network:   $NETWORK_MODE
  owner-visible process supervision: enabled

Press Ctrl+C to stop all services.
EOF

wait -n "${pids[@]}"
status=$?
exit "$status"
