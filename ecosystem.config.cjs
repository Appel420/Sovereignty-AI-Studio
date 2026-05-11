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
        BACKEND_URL: 'http://127.0.0.1:9897',
        WEATHER_URL: 'http://127.0.0.1:9897',
        GATEWAY_URL: 'http://127.0.0.1:9897',
        CORS_ORIGIN: 'http://localhost:9898',
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
      args: 'backend.app.main:app --host 127.0.0.1 --port 9897',
      interpreter: 'python3',
      cwd: './',
      env: {
        PYTHONPATH: '.:./backend',
        BACKEND_PORT: 9897,
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },

  ],
};
