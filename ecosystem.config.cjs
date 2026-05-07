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
        BACKEND_URL: 'http://127.0.0.1:9899',
        WEATHER_URL: 'http://127.0.0.1:9899',
        GATEWAY_URL: 'http://127.0.0.1:9898',
        CORS_ORIGIN: '*',
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },

    // ── Python Backend (FastAPI — port 9899) ──────────────────────────────
    {
      name: 'backend',
      script: 'uvicorn',
      args: 'backend.app.main:app --host 127.0.0.1 --port 9899',
      interpreter: 'python3',
      cwd: './',
      env: {
        PYTHONPATH: '.:./backend',
        BACKEND_PORT: 9899,
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },

    // ── Multi-Agent Gateway (port 9898) ───────────────────────────────────
    {
      name: 'gateway',
      script: 'gateway/main.py',
      interpreter: 'python3',
      cwd: './',
      env: {
        PYTHONPATH: '.:./backend',
        GATEWAY_PORT: 9898,
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },

    // ── SuperGrok TTS + Agent Bridge (standalone dev on 9898) ─────────────
    // NOTE: this is a separate local dev server and should not replace
    // node-bridge in normal production routing.
    {
      name: 'server-9898',
      script: 'server_9898.js',
      env: {
        PORT: 9898,
      },
      autorestart: false,
      watch: false,
    },
  ],
};
