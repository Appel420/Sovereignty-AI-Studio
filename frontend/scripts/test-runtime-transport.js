'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync(path.join(__dirname, 'transport.js'), 'utf8');
const context = { globalThis: {}, URL };
vm.createContext(context);
vm.runInContext(source, context);
const transport = context.globalThis.SovereignTransport;

assert.ok(transport, 'transport API did not initialize');
const offline = transport.config({ mode: 'offline' });
assert.strictEqual(offline.localOnly, true);
assert.strictEqual(transport.endpoint('/health', offline), 'http://127.0.0.1:9897/health');
assert.strictEqual(transport.nodeEndpoint('/health', offline), 'http://127.0.0.1:9899/health');
assert.strictEqual(transport.socketEndpoint('/ws', offline), 'ws://127.0.0.1:9899/ws');
assert.throws(() => transport.assertAllowed('https://example.invalid', offline), /External network/);

const secure = transport.config({
  mode: 'offline',
  httpOrigin: 'https://127.0.0.1:9897',
  nodeOrigin: 'https://127.0.0.1:9899',
  wsOrigin: 'wss://127.0.0.1:9899'
});
assert.strictEqual(transport.health(secure).transport, 'HTTPS/WSS');
assert.strictEqual(transport.socketEndpoint('/events', secure), 'wss://127.0.0.1:9899/events');

console.log('local transport tests passed');
