// ═══════════════════════════════════════════════════════════════════════════
// Sovereignty AI Studio — PM2 Ecosystem Configuration
// All services orchestrated through a single process manager.
// External traffic enters through node-bridge on port 9899.
// ═══════════════════════════════════════════════════════════════════════════
'use strict';

module.exports = {
  apps: [
    // ── Node.js Bridge (external gateway — port 9899) ─────────────────────
    {
      name: 'node-bridge',
      script: 'node-bridge/server.js',
      env: {
        NODE_BRIDGE_PORT: 9899,
        BACKEND_URL: 'http://127.0.0.1:8002',
        WEATHER_URL: 'http://127.0.0.1:8001',
        GATEWAY_URL: 'http://127.0.0.1:9001',
        CORS_ORIGIN: 'http://127.0.0.1:9898',
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },

    // ── Python Backend (bridge.py external backend — port 9897) ───────────
    {
      name: 'backend',
      script: 'uvicorn',
      args: 'backend.app.main:app --host 127.0.0.1 --port 8002',
      interpreter: 'python3',
      cwd: './',
      env: {
        PYTHONPATH: '.:./backend',
        BACKEND_PORT: 8002,
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },

  ],
};
