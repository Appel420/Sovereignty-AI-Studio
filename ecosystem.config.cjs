// ═══════════════════════════════════════════════════════════════════════════
// Sovereignty AI Studio — PM2 Ecosystem Configuration
// All services orchestrated through a single process manager.
// External traffic enters through node-bridge on port 9898.
// ═══════════════════════════════════════════════════════════════════════════
'use strict';

module.exports = {
  apps: [
    // ── Node.js Bridge (external gateway — port 9898) ─────────────────────
    {
      name: 'node-bridge',
      script: 'node-bridge/server.js',
      env: {
        NODE_BRIDGE_PORT: 9898,
        BACKEND_URL: 'http://127.0.0.1:8000',
        WEATHER_URL: 'http://127.0.0.1:8001',
        GATEWAY_URL: 'http://127.0.0.1:9000',
        CORS_ORIGIN: '*',
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },

    // ── Python Backend (FastAPI — port 8000) ──────────────────────────────
    {
      name: 'backend',
      script: 'uvicorn',
      args: 'backend.app.main:app --host 127.0.0.1 --port 8000',
      interpreter: 'python3',
      cwd: './',
      env: {
        PYTHONPATH: '.:./backend',
        BACKEND_PORT: 8000,
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },

    // ── Multi-Agent Gateway (port 9000) ───────────────────────────────────
    {
      name: 'gateway',
      script: 'gateway/main.py',
      interpreter: 'python3',
      cwd: './',
      env: {
        PYTHONPATH: '.:./backend',
        GATEWAY_PORT: 9000,
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },

    // ── SuperGrok TTS + Agent Bridge (port 9898 alt) ──────────────────────
    // NOTE: server-9898 conflicts with node-bridge on port 9898.
    // Only enable ONE of them. Use node-bridge for production (proxies to
    // gateway). Use server-9898 only for standalone TTS/agent development.
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
