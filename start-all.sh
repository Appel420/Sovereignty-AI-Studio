#!/usr/bin/env bash
# start-all.sh — Launch every service for Sovereignty AI Studio
# Works on iSH, Linux, macOS, and CI.

set -e

BRIDGE_PORT="${NODE_BRIDGE_PORT:-9899}"
PY_BRIDGE_PORT="${SG_PORT:-9897}"
WEATHER_PORT="${WEATHER_PORT:-8001}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
GATEWAY_PORT="${GATEWAY_PORT:-9898}"
PY_BRIDGE_URL="${SG_BRIDGE_URL:-ws://localhost:${PY_BRIDGE_PORT}}"

STARTED=""
SKIPPED=""

# Portable port-in-use check: tries nc first, then /dev/tcp fallback
_port_in_use() {
  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$1" >/dev/null 2>&1
  else
    (echo >/dev/tcp/127.0.0.1/"$1") >/dev/null 2>&1
  fi
}

wait_for_port_free() {
  local port="$1"
  local timeout="${2:-15}"
  local start elapsed
  start=$(date +%s)
  while _port_in_use "$port"; do
    elapsed=$(( $(date +%s) - start ))
    if [ "$elapsed" -ge "$timeout" ]; then
      echo "[warn] port $port still busy after ${timeout}s; skipping start for that service"
      return 1
    fi
    echo "[wait] port $port busy, retrying..."
    sleep 1
  done
  return 0
}

cleanup() {
  echo ""
  echo "[stop] shutting down..."
  [ -n "$PY_BRIDGE_PID" ] && kill "$PY_BRIDGE_PID" 2>/dev/null
  [ -n "$REDIS_PID" ]   && kill "$REDIS_PID"   2>/dev/null
  [ -n "$WEATHER_PID" ] && kill "$WEATHER_PID" 2>/dev/null
  [ -n "$GATEWAY_PID" ] && kill "$GATEWAY_PID" 2>/dev/null
  [ -n "$BRIDGE_PID" ]  && kill "$BRIDGE_PID"  2>/dev/null
  exit 0
}
trap cleanup INT TERM

# --- Python bridge.py (must be started before node-bridge) ---
if wait_for_port_free "$PY_BRIDGE_PORT"; then
  echo "[start] python bridge.py on port $PY_BRIDGE_PORT"
  SG_PORT="$PY_BRIDGE_PORT" python3 bridge.py &
  PY_BRIDGE_PID=$!
  sleep 2
  STARTED="${STARTED} py-bridge"
else
  echo "[skip] python bridge.py not started (port $PY_BRIDGE_PORT busy)"
  echo "[info] assuming an existing bridge.py is already running on :$PY_BRIDGE_PORT"
fi

# --- Redis (optional — skip if already running) ---
if command -v redis-server >/dev/null 2>&1; then
  if ! redis-cli ping >/dev/null 2>&1; then
    echo "[start] redis on port 6379"
    redis-server --daemonize yes
    REDIS_PID=$(cat /var/run/redis.pid 2>/dev/null || echo "")
    STARTED="${STARTED} redis"
  else
    echo "[skip]  redis already running"
  fi
else
  echo "[skip]  redis not installed"
fi

# --- Quart weather dashboard ---
if wait_for_port_free "$WEATHER_PORT"; then
  echo "[start] weather dashboard on port $WEATHER_PORT"
  PYTHONPATH=.:./backend hypercorn weather_dashboard:app \
    --bind "0.0.0.0:$WEATHER_PORT" &
  WEATHER_PID=$!
  sleep 2
  STARTED="${STARTED} weather"
else
  echo "[skip] weather dashboard not started (port $WEATHER_PORT busy)"
  SKIPPED="${SKIPPED} weather(:$WEATHER_PORT)"
fi

# --- Multi-agent gateway ---
if wait_for_port_free "$GATEWAY_PORT"; then
  echo "[start] multi-agent gateway on port $GATEWAY_PORT"
  PYTHONPATH=.:./backend GATEWAY_PORT="$GATEWAY_PORT" \
    python3 gateway/main.py &
  GATEWAY_PID=$!
  sleep 2
  STARTED="${STARTED} gateway"
else
  echo "[skip] gateway not started (port $GATEWAY_PORT busy)"
  SKIPPED="${SKIPPED} gateway(:$GATEWAY_PORT)"
fi

# --- Node.js bridge ---
if wait_for_port_free "$BRIDGE_PORT"; then
  echo "[start] node-bridge on port $BRIDGE_PORT"
  cd node-bridge
  WEATHER_URL="http://localhost:$WEATHER_PORT" \
  BACKEND_URL="http://localhost:$BACKEND_PORT" \
  GATEWAY_URL="http://localhost:$GATEWAY_PORT" \
  SG_BRIDGE_URL="$PY_BRIDGE_URL" \
  NODE_BRIDGE_PORT="$BRIDGE_PORT" \
    node server.js &
  BRIDGE_PID=$!
  cd ..
  sleep 2
  STARTED="${STARTED} bridge"
else
  echo "[skip] node-bridge not started (port $BRIDGE_PORT busy)"
  SKIPPED="${SKIPPED} bridge(:$BRIDGE_PORT)"
fi

echo ""
if [ -n "$SKIPPED" ]; then
  echo "=== WARNING: Some services were skipped ==="
  echo "  Skipped:${SKIPPED}"
  echo "  Started:${STARTED}"
  # Exit non-zero if the bridge (required gateway) was skipped
  case "$SKIPPED" in *bridge*) echo "[error] Bridge is a required service. Exiting."; exit 1;; esac
else
  echo "=== All services running ==="
fi
echo "  Bridge:   http://localhost:$BRIDGE_PORT/health"
echo "  PyBridge: ws://localhost:$PY_BRIDGE_PORT"
echo "  Gateway:  http://localhost:$GATEWAY_PORT/health"
echo "  Weather:  http://localhost:$WEATHER_PORT/api/weather?city=London"
echo "  Agents:   http://localhost:$BRIDGE_PORT/api/agents/status"
echo "  WS:       ws://localhost:$BRIDGE_PORT/ws/alerts"
echo ""
echo "Press Ctrl+C to stop all services."

# Keep the script alive
wait
