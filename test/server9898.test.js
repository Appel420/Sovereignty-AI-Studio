'use strict';

/**
 * Tests for the canonical node bridge on port 9899.
 *
 * Run with:  node --test test/server9898.test.js
 */

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const { WebSocket } = require('ws');

// Import the bridge under test; it is safe to listen on an ephemeral port.
const { server } = require('../node-bridge/server');

let baseUrl;

before(async () => {
  await new Promise((resolve) => {
    server.listen(0, () => {
      const addr = server.address();
      baseUrl = `http://localhost:${addr.port}`;
      resolve();
    });
  });
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));
});

/* ── helpers ────────────────────────────────────────────────── */

function request(urlPath, opts = {}) {
  const url = new URL(urlPath, baseUrl);
  return new Promise((resolve, reject) => {
    const req = http.request(url, {
      method:  opts.method  || 'GET',
      headers: opts.headers || {},
    }, (res) => {
      let body = '';
      res.on('data', (d) => (body += d));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(body) }); }
        catch (e) { /* JSON parse failed — return raw body string */ resolve({ status: res.statusCode, body }); }
      });
    });
    req.on('error', reject);
    if (opts.body) req.write(opts.body);
    req.end();
  });
}

/* ── /health ────────────────────────────────────────────────── */

describe('node-bridge — /health', () => {
  it('returns healthy status', async () => {
    const r = await request('/health');
    assert.equal(r.status, 200);
    assert.equal(r.body.status, 'healthy');
    assert.equal(r.body.service, 'node-bridge');
    assert.ok(typeof r.body.uptime === 'number');
    assert.ok(r.body.timestamp);
    assert.ok(typeof r.body.backends === 'object');
  });
});

/* ── /api/agents/status ─────────────────────────────────────── */

describe('node-bridge — /api/agents/status', () => {
  it('returns an ecosystem status payload', async () => {
    const r = await request('/api/agents/status');
    assert.equal(r.status, 200);
    assert.ok(r.body.ecosystem);
    assert.ok(r.body.agents);
    assert.ok(r.body.agents.gateway);
    assert.ok(r.body.agents.py_bridge);
  });
});

/* ── /api/bridge/status ─────────────────────────────────────── */

describe('node-bridge — /api/bridge/status', () => {
  it('returns bridge connectivity data', async () => {
    const r = await request('/api/bridge/status');
    assert.equal(r.status, 200);
    assert.equal(r.body.status, 'healthy');
    assert.ok(r.body.services);
    assert.ok('api' in r.body.services);
    assert.ok('py_bridge' in r.body.services);
  });
});

/* ── CORS ───────────────────────────────────────────────────── */

describe('node-bridge — CORS', () => {
  it('OPTIONS preflight returns 204 with CORS headers', async () => {
    const r = await request('/health', { method: 'OPTIONS' });
    assert.equal(r.status, 204);
  });
});

/* ── 404 ─────────────────────────────────────────────────────── */

describe('node-bridge — 404', () => {
  it('unknown routes return 404', async () => {
    const r = await request('/unknown-route');
    assert.equal(r.status, 404);
  });
});

/* ── WebSocket ───────────────────────────────────────────────── */

describe('node-bridge — WebSocket', () => {
  it('responds to ping with pong', async () => {
    const addr = server.address();
    const ws = new WebSocket(`ws://localhost:${addr.port}/ws/alerts`);

    const pong = await new Promise((resolve, reject) => {
      ws.on('open', () => ws.send(JSON.stringify({ type: 'ping' })));
      ws.on('message', (raw) => { resolve(JSON.parse(raw)); ws.close(); });
      ws.on('error', reject);
      setTimeout(() => reject(new Error('ws ping timeout')), 3000);
    });

    assert.equal(pong.type, 'pong');
    assert.ok(pong.timestamp);
  });

  it('returns status for STATUS command', async () => {
    const addr = server.address();
    const ws = new WebSocket(`ws://localhost:${addr.port}/ws/alerts`);

    const reply = await new Promise((resolve, reject) => {
      ws.on('open', () => ws.send(JSON.stringify({ cmd: 'STATUS' })));
      ws.on('message', (raw) => { resolve(JSON.parse(raw)); ws.close(); });
      ws.on('error', reject);
      setTimeout(() => reject(new Error('ws status timeout')), 5000);
    });

    assert.equal(reply.type, 'status');
    assert.equal(reply.bridge, 'online');
  });
});
