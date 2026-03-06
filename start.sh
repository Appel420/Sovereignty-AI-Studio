#!/bin/bash
set -e
echo "=== SuperGrok Security Stack ==="
echo ""

# 1. Check Python deps
pip install fastapi uvicorn pydantic --quiet --break-system-packages 2>/dev/null

# 2. Start security backend on 8443
echo "► Starting security backend on :8443"
cd "$(dirname "$0")"
python3 security_backend.py &
BACKEND_PID=$!
echo "  PID: $BACKEND_PID"
sleep 1

# 3. Health check
if curl -s http://127.0.0.1:8443/health >/dev/null 2>&1; then
  echo "  ✅ Backend healthy"
else
  echo "  ⚠️  Backend not responding (check port 8443)"
fi

# 4. Start bridge on 9898 (if server_9898.js exists)
if [ -f "../server_9898.js" ]; then
  echo "► Starting Piper bridge on :9898"
  node ../server_9898.js &
  BRIDGE_PID=$!
  echo "  PID: $BRIDGE_PID"
fi

echo ""
echo "► Open: SuperGrok_v13_SECURED.html"
echo ""
echo "Press Ctrl+C to stop all services"

# Save PIDs for cleanup
echo "$BACKEND_PID" > .pids
[ -n "$BRIDGE_PID" ] && echo "$BRIDGE_PID" >> .pids

wait
