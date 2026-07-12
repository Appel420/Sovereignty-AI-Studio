const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const { WebSocket } = require('ws');

const { app, server, wss } = require('../server');

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
  for (const c of wss.clients) c.terminate();
  await new Promise((resolve) => server.close(resolve));
});

function request(path, opts = {}) {
  const url = new URL(path, baseUrl);
  return new Promise((resolve, reject) => {
    const req = http.request(url, {
      method: opts.method || 'GET',
      headers: opts.headers || {},
    }, (res) => {
      let body = '';
      res.on('data', (d) => (body += d));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(body) }); }
        catch { resolve({ status: res.statusCode, body }); }
      });
    });
    req.on('error', reject);
    if (opts.body) req.write(opts.body);
    req.end();
  });
}

describe('Node Bridge – Health', () => {
  it('GET /health returns status and backend info', async () => {
    const r = await request('/health');
    assert.equal(r.status, 200);
    assert.equal(r.body.status, 'healthy');
    assert.equal(r.body.service, 'node-bridge');
    assert.ok(/^http:\/\/(localhost|127\.0\.0\.1):8002$/.test(r.body.backends.api));
    assert.ok(/^http:\/\/(localhost|127\.0\.0\.1):8001$/.test(r.body.backends.weather));
    assert.ok(r.body.timestamp);
  });

  it('reports offline mode and local CA as the default transport policy', async () => {
    const r = await request('/api/network/status');
    assert.equal(r.status, 200);
    assert.equal(r.body.offline_mode, true);
    assert.equal(r.body.network_mode, 'offline');
    assert.equal(r.body.remote_network_enabled, false);
    assert.equal(r.body.tls_mode, 'local-ca');
  });

  it('blocks an external proxy target without opening an outbound connection', async () => {
    const r = await request('/proxy/fetch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://example.com/' }),
    });
    assert.equal(r.status, 503);
    assert.equal(r.body.code, 'OFFLINE_NETWORK_BLOCKED');
  });
});

describe('Node Bridge – Notify', () => {
  it('rejects missing fields', async () => {
    const r = await request('/api/bridge/notify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'no type' }),
    });
    assert.equal(r.status, 400);
  });

  it('accepts valid payload', async () => {
    const r = await request('/api/bridge/notify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'test', title: 'Hello' }),
    });
    assert.equal(r.status, 200);
    assert.equal(r.body.alert.type, 'test');
    assert.equal(r.body.alert.title, 'Hello');
    assert.equal(r.body.alert.severity, 'info');
  });
});

describe('Node Bridge – WebSocket', () => {
  it('responds to ping with pong', async () => {
    const addr = server.address();
    const ws = new WebSocket(`ws://localhost:${addr.port}/ws/alerts`);

    const pong = await new Promise((resolve, reject) => {
      ws.on('open', () => ws.send(JSON.stringify({ type: 'ping' })));
      ws.on('message', (raw) => { resolve(JSON.parse(raw)); ws.close(); });
      ws.on('error', reject);
      setTimeout(() => reject(new Error('timeout')), 3000);
    });

    assert.equal(pong.type, 'pong');
    assert.ok(pong.timestamp);
  });

  it('broadcasts notifications to connected clients', async () => {
    const addr = server.address();
    const ws = new WebSocket(`ws://localhost:${addr.port}/ws/alerts`);
    await new Promise((r) => ws.on('open', r));

    const msgPromise = new Promise((resolve, reject) => {
      ws.on('message', (raw) => { resolve(JSON.parse(raw)); ws.close(); });
      setTimeout(() => reject(new Error('timeout')), 3000);
    });

    await request('/api/bridge/notify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'alert', title: 'Broadcast', severity: 'warning' }),
    });

    const msg = await msgPromise;
    assert.equal(msg.type, 'alert');
    assert.equal(msg.title, 'Broadcast');
    assert.equal(msg.severity, 'warning');
  });
});

describe('Node Bridge – Status', () => {
  it('GET /api/bridge/status returns service health', async () => {
    const r = await request('/api/bridge/status');
    assert.equal(r.status, 200);
    assert.equal(r.body.status, 'healthy');
    assert.ok(r.body.services);
    assert.ok(r.body.timestamp);
    assert.equal(typeof r.body.websocket_clients, 'number');
    assert.equal(typeof r.body.uptime, 'number');
  });
});
