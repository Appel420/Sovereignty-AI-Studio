const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const { WebSocket } = require('ws');

const { app, server, wss } = require('../server');

let baseUrl;

before(async () => {
  await new Promise((resolve) => {
    server.listen(0, () => {                 // OS picks a free port
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

/* ---- helpers ---- */
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

/* ---- tests ---- */
describe('Node Bridge – Health', () => {
  it('GET /health returns status and backend info', async () => {
    const r = await request('/health');
    assert.equal(r.status, 200);
    assert.equal(r.body.status, 'healthy');
    assert.equal(r.body.service, 'node-bridge');
    assert.equal(r.body.backends.api, 'http://127.0.0.1:8002');
    assert.equal(r.body.backends.weather, 'http://127.0.0.1:8001');
    assert.equal(r.body.backends.gateway, 'http://127.0.0.1:9001');
    assert.ok(r.body.timestamp);
  });
});

describe('Node Bridge – OAuth hardening', () => {
  it('rejects Google/Meta OAuth hosts for token exchange', async () => {
    const prev = process.env.KEYCLOAK_URL;
    process.env.KEYCLOAK_URL = 'https://accounts.google.com';
    try {
      const r = await request('/keycloak/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grant_type: 'client_credentials' }),
      });
      assert.equal(r.status, 403);
      assert.equal(r.body.success, false);

      process.env.KEYCLOAK_URL = 'https://graph.facebook.com';
      const rMeta = await request('/keycloak/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grant_type: 'client_credentials' }),
      });
      assert.equal(rMeta.status, 403);
      assert.equal(rMeta.body.success, false);
    } finally {
      if (prev === undefined) delete process.env.KEYCLOAK_URL;
      else process.env.KEYCLOAK_URL = prev;
    }
  });

  it('proxies token exchange to Keycloak OpenID token endpoint', async () => {
    const prevUrl = process.env.KEYCLOAK_URL;
    const prevRealm = process.env.KEYCLOAK_REALM;
    let seenPath = '';
    const mock = http.createServer((req, res) => {
      seenPath = req.url || '';
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ access_token: 'local-token' }));
    });
    await new Promise((resolve) => mock.listen(0, '127.0.0.1', resolve));
    const addr = mock.address();
    process.env.KEYCLOAK_URL = `http://127.0.0.1:${addr.port}`;
    process.env.KEYCLOAK_REALM = 'sovereignty';
    try {
      const r = await request('/keycloak/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'grant_type=client_credentials',
      });
      assert.equal(r.status, 200);
      assert.equal(r.body.access_token, 'local-token');
      assert.equal(seenPath, '/realms/sovereignty/protocol/openid-connect/token');
    } finally {
      await new Promise((resolve) => mock.close(resolve));
      if (prevUrl === undefined) delete process.env.KEYCLOAK_URL;
      else process.env.KEYCLOAK_URL = prevUrl;
      if (prevRealm === undefined) delete process.env.KEYCLOAK_REALM;
      else process.env.KEYCLOAK_REALM = prevRealm;
    }
  });

  it('returns 502 when Keycloak endpoint is unreachable', async () => {
    const prev = process.env.KEYCLOAK_URL;
    process.env.KEYCLOAK_URL = 'http://127.0.0.1:1';
    try {
      const r = await request('/keycloak/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grant_type: 'client_credentials' }),
      });
      assert.equal(r.status, 502);
      assert.equal(r.body.error, 'Backend unavailable');
    } finally {
      if (prev === undefined) delete process.env.KEYCLOAK_URL;
      else process.env.KEYCLOAK_URL = prev;
    }
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

    // listener first, then POST
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
