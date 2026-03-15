#!/bin/sh
# start-all.sh — Launch every service for Sovereignty AI Studio
# Works on iSH, Linux, macOS, and CI.

set -e

BRIDGE_PORT="${NODE_BRIDGE_PORT:-9898}"
WEATHER_PORT="${WEATHER_PORT:-8001}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

wait_for_port_free() {
  PORT="$1"
  TIMEOUT="${2:-15}"
  START=$(date +%s)
  while nc -z 127.0.0.1 "$PORT" >/dev/null 2>&1; do
    ELAPSED=$(( $(date +%s) - START ))
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
      echo "[warn] port $PORT still busy after ${TIMEOUT}s; skipping start for that service"
      return 1
    fi
    echo "[wait] port $PORT busy, retrying..."
    sleep 1
  done
  return 0
}

cleanup() {
  echo ""
  echo "[stop] shutting down..."
  [ -n "$REDIS_PID" ]   && kill "$REDIS_PID"   2>/dev/null
  [ -n "$WEATHER_PID" ] && kill "$WEATHER_PID" 2>/dev/null
  [ -n "$BRIDGE_PID" ]  && kill "$BRIDGE_PID"  2>/dev/null
  exit 0
}
trap cleanup INT TERM

# --- Redis (optional — skip if already running) ---
if command -v redis-server >/dev/null 2>&1; then
  if ! redis-cli ping >/dev/null 2>&1; then
    echo "[start] redis on port 6379"
    redis-server --daemonize yes
    REDIS_PID=$(cat /var/run/redis.pid 2>/dev/null || echo "")
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
else
  echo "[skip] weather dashboard not started (port busy)"
fi

# --- Node.js bridge ---
if wait_for_port_free "$BRIDGE_PORT"; then
  echo "[start] node-bridge on port $BRIDGE_PORT"
  cd node-bridge
  WEATHER_URL="http://localhost:$WEATHER_PORT" \
  BACKEND_URL="http://localhost:$BACKEND_PORT" \
  NODE_BRIDGE_PORT="$BRIDGE_PORT" \
    node server.js &
  BRIDGE_PID=$!
  cd ..
  sleep 2
else
  echo "[skip] node-bridge not started (port busy)"
fi

echo ""
echo "=== All services running ==="
echo "  Bridge:   http://localhost:$BRIDGE_PORT/health"
echo "  Weather:  http://localhost:$WEATHER_PORT/api/weather?city=London"
echo "  WS:       ws://localhost:$BRIDGE_PORT/ws/alerts"
echo ""
echo "Press Ctrl+C to stop all services."

# Keep the script alive
wait
