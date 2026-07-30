'use strict';

const { webcrypto } = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync(path.join(__dirname, 'hawking-channel.js'), 'utf8');
const events = [];
const eventTarget = { dispatchEvent: event => events.push(event) };
const context = {
  globalThis: {},
  document: eventTarget,
  crypto: webcrypto,
  CustomEvent: function (name, init) { this.type = name; this.detail = init.detail; },
  btoa: value => Buffer.from(value, 'binary').toString('base64'),
  atob: value => Buffer.from(value, 'base64').toString('binary'),
  TextEncoder,
  TextDecoder,
  URL,
  setTimeout
};

vm.createContext(context);
vm.runInContext(source, context);
const api = context.globalThis.SovereignHawkingChannel;
assert.ok(api);
assert.strictEqual(api.STATUS.READY, 'READY');

(async () => {
  const channel = api.create({ eventTarget, crypto: webcrypto, CustomEvent: context.CustomEvent });
  assert.strictEqual(channel.getStatus(), 'INIT');
  await channel.init();
  assert.strictEqual(channel.getStatus(), 'READY');
  assert.ok(channel.getFingerprint());

  const sent = await channel.send('local message', { mode: 'offline' });
  assert.strictEqual(sent.path, 'local');
  assert.strictEqual(sent.ok, true);
  assert.strictEqual(events.length, 1);
  assert.strictEqual(events[0].type, 'sg:hawkingMsg');
  assert.strictEqual(await channel.verify(sent.envelope), true);
  assert.strictEqual(await channel.unseal(sent.envelope), 'local message');

  const tampered = Object.assign({}, sent.envelope, { ciphertext: sent.envelope.ciphertext.slice(0, -1) + 'A' });
  await assert.rejects(() => channel.unseal(tampered), /signature verification failed|operation|Invalid/);

  const unavailable = await channel.send('not sent', { mode: 'online' });
  assert.strictEqual(unavailable.ok, false);
  assert.strictEqual(unavailable.reason, 'transport_not_configured');

  console.log('Hawking local encryption, signature verification, and transport tests passed');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
