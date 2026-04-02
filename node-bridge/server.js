/**
 * Sovereignty AI Studio — Node.js Communication Bridge
 *
 * Connects the React frontend, Python backends (FastAPI + Quart), and
 * iSH / Code Pad developer environments through a single entry-point.
 *
 * Endpoints:
 *   GET  /health                  – bridge health check
 *   ALL  /api/v1/*                – proxy to FastAPI  (BACKEND_URL)
 *   ALL  /api/weather*            – proxy to Quart    (WEATHER_URL)
 *   ALL  /api/forecast*           – proxy to Quart    (WEATHER_URL)
 *   POST /ai/:agentId             – AI agent bridge   (GATEWAY_URL)
 *   ALL  /api/chat                – proxy to Gateway   (GATEWAY_URL)
 *   ALL  /api/voice               – proxy to Gateway   (GATEWAY_URL)
 *   ALL  /api/plugins/*           – proxy to Gateway   (GATEWAY_URL)
 *   ALL  /api/judge/*             – proxy to Gateway   (GATEWAY_URL)
 *   GET  /api/agents/status       – aggregated ecosystem health
 *   POST /api/bridge/notify       – push real-time alert to WebSocket clients
 *   GET  /api/bridge/status       – aggregated backend service health
 *   WS   /ws/alerts               – WebSocket for live alerts
 */

const express = require('express');
const http = require('http');
const https = require('https');
const fs = require('fs');
const { WebSocketServer } = require('ws');

// ---------------------------------------------------------------------------
// Config from environment (sensible defaults for local / iSH)
// ---------------------------------------------------------------------------
const PORT = parseInt(process.env.NODE_BRIDGE_PORT || '9898', 10);
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const WEATHER_URL = process.env.WEATHER_URL || 'http://localhost:8001';
const GATEWAY_URL = process.env.GATEWAY_URL || 'http://localhost:9000';
const TLS_CERT = process.env.TLS_CERT || '';
const TLS_KEY = process.env.TLS_KEY || '';
const UPSTREAM_DEFAULT_PORT = parseInt(process.env.UPSTREAM_DEFAULT_PORT || '9898', 10);

const app = express();
app.use(express.json());

// ---------------------------------------------------------------------------
// CORS — default to bridge origin
// ---------------------------------------------------------------------------
app.use((_req, res, next) => {
  const origin = process.env.CORS_ORIGIN || `http://localhost:${PORT}`;
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PATCH,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (_req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
app.get('/health', (_req, res) => {
  res.json({
    status: 'healthy',
    service: 'node-bridge',
    uptime: process.uptime(),
    backends: { api: BACKEND_URL, weather: WEATHER_URL, gateway: GATEWAY_URL },
    timestamp: new Date().toISOString(),
  });
});

// ---------------------------------------------------------------------------
// Lightweight reverse proxy (no extra dependency)
// ---------------------------------------------------------------------------
function requestClientFor(url) {
  return url.protocol === 'https:' ? https : http;
}

function resolveUpstreamPort(url) {
  return url.port || UPSTREAM_DEFAULT_PORT;
}

function proxyRequest(targetBase, req, res) {
  const url = new URL(req.originalUrl, targetBase);
  const client = requestClientFor(url);
  const options = {
    hostname: url.hostname,
    port: resolveUpstreamPort(url),
    path: url.pathname + url.search,
    method: req.method,
    headers: { ...req.headers, host: url.host },
  };

  const proxyReq = client.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on('error', (err) => {
    console.error(`[proxy] ${targetBase} error:`, err.message);
    if (!res.headersSent) {
      res.status(502).json({ error: 'Backend unavailable', target: targetBase });
    }
  });

  req.pipe(proxyReq, { end: true });
}

// Proxy /api/v1/* → FastAPI
app.use('/api/v1', (req, res) => proxyRequest(BACKEND_URL, req, res));

// Proxy /api/weather* and /api/forecast* → Quart
app.use('/api/weather', (req, res) => proxyRequest(WEATHER_URL, req, res));
app.use('/api/forecast', (req, res) => proxyRequest(WEATHER_URL, req, res));

// ---------------------------------------------------------------------------
// Agent / Gateway proxy — routes agent traffic to the multi-agent gateway
// ---------------------------------------------------------------------------

// POST /ai/:agentId — AI agent bridge (called by SGHv119.html orchestrator)
app.post('/ai/:agentId', (req, res) => {
  // Sanitize agent ID to alphanumeric, underscore, hyphen only
  const agentId = (req.params.agentId || '').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 64);
  if (!agentId) {
    return res.status(400).json({ error: 'Invalid agent ID' });
  }
  const body = req.body || {};
  const payload = JSON.stringify({
    prompt: (body.messages && body.messages.length)
      ? body.messages[body.messages.length - 1].content
      : '',
    system: (body.messages && body.messages.length > 1)
      ? body.messages[0].content
      : undefined,
    task_type: body.task_type || 'general',
    model: body.model,
    max_tokens: body.max_tokens || 1024,
  });

  const url = new URL('/api/chat', GATEWAY_URL);
  const options = {
    hostname: url.hostname,
    port: resolveUpstreamPort(url),
    path: url.pathname,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-SG-Agent': agentId,
      'Content-Length': Buffer.byteLength(payload),
    },
  };

  const client = requestClientFor(url);
  const proxyReq = client.request(options, (proxyRes) => {
    let data = '';
    proxyRes.on('data', (chunk) => { data += chunk; });
    proxyRes.on('end', () => {
      try {
        const result = JSON.parse(data);
        // Wrap in OpenAI-compatible format for SGHv119.html bridge() function
        res.json({
          choices: [{
            message: { content: result.result || result.error || data, role: 'assistant' },
          }],
          agent: agentId,
          timestamp: new Date().toISOString(),
        });
      } catch {
        res.json({
          choices: [{ message: { content: data || 'No response', role: 'assistant' } }],
          agent: agentId,
          timestamp: new Date().toISOString(),
        });
      }
    });
  });

  proxyReq.on('error', (err) => {
    console.error('[ai-proxy] gateway error for %s: %s', agentId, err.message);
    res.json({
      choices: [{ message: { content: '[' + agentId + ' offline] Gateway unreachable', role: 'assistant' } }],
      agent: agentId,
      error: true,
    });
  });

  proxyReq.write(payload);
  proxyReq.end();
});

// Proxy /api/chat → Gateway
app.use('/api/chat', (req, res) => proxyRequest(GATEWAY_URL, req, res));

// Proxy /api/voice → Gateway
app.use('/api/voice', (req, res) => proxyRequest(GATEWAY_URL, req, res));

// Proxy /api/plugins/* → Gateway
app.use('/api/plugins', (req, res) => proxyRequest(GATEWAY_URL, req, res));

// Proxy /api/judge/* → Gateway
app.use('/api/judge', (req, res) => proxyRequest(GATEWAY_URL, req, res));

// GET /api/agents/status — aggregated ecosystem agent health
app.get('/api/agents/status', async (_req, res) => {
  const agents = {
    gateway: { url: GATEWAY_URL, status: 'offline', port: 9000 },
    backend: { url: BACKEND_URL, status: 'offline', port: 8000 },
    weather: { url: WEATHER_URL, status: 'offline', port: 8001 },
  };

  const checkAgent = (key) =>
    new Promise((resolve) => {
      const target = new URL('/health', agents[key].url);
      const client = requestClientFor(target);
      const req = client.request({
        hostname: target.hostname,
        port: resolveUpstreamPort(target),
        path: target.pathname + target.search,
        method: 'GET',
        timeout: 3000,
      }, (r) => {
        let data = '';
        r.on('data', (chunk) => { data += chunk; });
        r.on('end', () => {
          if (r.statusCode && r.statusCode < 500) {
            agents[key].status = 'online';
            try { agents[key].detail = JSON.parse(data); } catch { /* skip */ }
          }
          resolve();
        });
      });
      req.setTimeout(3000, () => { req.destroy(); resolve(); });
      req.on('error', () => resolve());
      req.end();
    });

  await Promise.all(Object.keys(agents).map(checkAgent));

  const onlineCount = Object.values(agents).filter((a) => a.status === 'online').length;
  res.json({
    ecosystem: onlineCount === Object.keys(agents).length ? 'healthy' : onlineCount > 0 ? 'degraded' : 'offline',
    agents,
    bridge: { status: 'online', uptime: process.uptime(), websocket_clients: clients.size },
    timestamp: new Date().toISOString(),
  });
});

// ---------------------------------------------------------------------------
// WebSocket — real-time alert channel
// ---------------------------------------------------------------------------
const useTLS = TLS_CERT && TLS_KEY && fs.existsSync(TLS_CERT) && fs.existsSync(TLS_KEY);
const server = useTLS
  ? https.createServer({ cert: fs.readFileSync(TLS_CERT), key: fs.readFileSync(TLS_KEY) }, app)
  : http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws/alerts' });
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log(`[ws] client connected (${clients.size} total)`);

  ws.on('close', () => {
    clients.delete(ws);
    console.log(`[ws] client disconnected (${clients.size} total)`);
  });

  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw);
      if (msg.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
      }
    } catch {
      // ignore malformed messages
    }
  });
});

function broadcast(data) {
  const payload = JSON.stringify(data);
  for (const ws of clients) {
    if (ws.readyState === 1) ws.send(payload);  // 1 === WebSocket.OPEN
  }
}

// GET /api/bridge/status — aggregated service connectivity
app.get('/api/bridge/status', async (_req, res) => {
  const services = { api: 'offline', weather: 'offline', gateway: 'offline' };

  const checkService = (url, key) =>
    new Promise((resolve) => {
      const target = new URL('/health', url);
      const client = requestClientFor(target);
      const req = client.request({
        hostname: target.hostname,
        port: resolveUpstreamPort(target),
        path: target.pathname + target.search,
        method: 'GET',
      }, (r) => {
        if (r.statusCode && r.statusCode < 500) services[key] = 'online';
        r.resume();
        resolve();
      });
      req.setTimeout(3000, () => { req.destroy(); resolve(); });
      req.on('error', () => resolve());
      req.end();
    });

  await Promise.all([
    checkService(BACKEND_URL, 'api'),
    checkService(WEATHER_URL, 'weather'),
    checkService(GATEWAY_URL, 'gateway'),
  ]);

  res.json({
    status: 'healthy',
    services,
    websocket_clients: clients.size,
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

// POST /api/bridge/notify — Python backends can push alerts here
app.post('/api/bridge/notify', (req, res) => {
  const { type, title, message, severity } = req.body;
  if (!type || !title) {
    return res.status(400).json({ error: 'type and title are required' });
  }
  const alert = {
    type,
    title,
    message: message || '',
    severity: severity || 'info',
    timestamp: new Date().toISOString(),
  };
  broadcast(alert);
  res.json({ sent: clients.size, alert });
});

// ---------------------------------------------------------------------------
// Start (only when run directly, not when imported for tests)
// ---------------------------------------------------------------------------
if (require.main === module) {
  server.listen(PORT, () => {
    const proto = useTLS ? 'https' : 'http';
    const wsproto = useTLS ? 'wss' : 'ws';
    console.log(`[node-bridge] listening on ${proto}://localhost:${PORT}${useTLS ? ' (TLS)' : ''}`);
    console.log(`[node-bridge] WebSocket   ${wsproto}://localhost:${PORT}/ws/alerts`);
    console.log(`[node-bridge] proxy /api/v1/*      → ${BACKEND_URL}`);
    console.log(`[node-bridge] proxy /api/weather/*  → ${WEATHER_URL}`);
    console.log(`[node-bridge] proxy /api/forecast/* → ${WEATHER_URL}`);
    console.log(`[node-bridge] proxy /ai/*           → ${GATEWAY_URL}`);
    console.log(`[node-bridge] proxy /api/chat       → ${GATEWAY_URL}`);
    console.log(`[node-bridge] proxy /api/voice      → ${GATEWAY_URL}`);
    console.log(`[node-bridge] proxy /api/plugins/*  → ${GATEWAY_URL}`);
    console.log(`[node-bridge] proxy /api/judge/*    → ${GATEWAY_URL}`);
  });
}

module.exports = { app, server, wss, broadcast };
