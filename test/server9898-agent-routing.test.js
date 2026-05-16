'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const { spawn } = require('child_process');
const { WebSocket } = require('ws');

const SERVER_URL = 'ws://127.0.0.1:9899';
let serverProc;

function waitForWsOpen(url, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const started = Date.now();

    function tryConnect() {
      const ws = new WebSocket(url);
      ws.on('open', () => resolve(ws));
      ws.on('error', () => {
        ws.close();
        if (Date.now() - started > timeoutMs) {
          reject(new Error('Timed out waiting for WS server'));
        } else {
          setTimeout(tryConnect, 200);
        }
      });
    }

    tryConnect();
  });
}

function waitForType(ws, expectedType, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Timed out waiting for ' + expectedType)), timeoutMs);
    ws.on('message', (raw) => {
      let msg;
      try { msg = JSON.parse(raw); } catch { return; }
      if (msg.type === expectedType) {
        clearTimeout(timeout);
        resolve(msg);
      }
    });
    ws.on('error', (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}

describe('server_9899 agent routing', () => {
  before(async () => {
    serverProc = spawn('node', ['server_9899.js'], {
      cwd: path.resolve(__dirname, '..'),
      stdio: 'ignore',
    });
    await waitForWsOpen(SERVER_URL).then((ws) => ws.close());
  });

  after(async () => {
    if (serverProc && !serverProc.killed) {
      serverProc.kill('SIGINT');
    }
  });

  it('returns agent_response for gpt agent_request', async () => {
    const ws = await waitForWsOpen(SERVER_URL);

    ws.send(JSON.stringify({
      type: 'agent_request',
      agent: 'gpt',
      payload: { prompt: 'health check' },
    }));

    const reply = await waitForType(ws, 'agent_response');
    ws.close();

    assert.equal(reply.agent, 'gpt');
    assert.ok(reply.payload);
    assert.equal(reply.payload.error, true);
    assert.ok(reply.payload.text.length > 0);
  });

  it('returns unknown agent error for unsupported agent', async () => {
    const ws = await waitForWsOpen(SERVER_URL);

    ws.send(JSON.stringify({
      type: 'agent_request',
      agent: 'unsupported-agent',
      payload: { prompt: 'test' },
    }));

    const reply = await waitForType(ws, 'agent_response');
    ws.close();

    assert.equal(reply.agent, 'unsupported-agent');
    assert.equal(reply.payload.error, true);
    assert.ok(reply.payload.text.length > 0);
  });
});
