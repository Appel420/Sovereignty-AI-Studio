'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { SGHV119HawkingRuntime, SGHV119Message, SGHV119Bus } = require('./hawking-runtime.js');

function envelope(overrides) {
  return {
    version: 1,
    timestamp: 1700000000000,
    message_id: 'message-001',
    sender_id: 'local-owner',
    action: 'dashboard.refresh',
    nonce: 'nonce-001',
    sequence: 1,
    ciphertext: 'sealed',
    signature: 'valid',
    ...(overrides || {})
  };
}

function harness(options) {
  options = options || {};
  const published = [];
  const scar = [];
  const channel = options.channel || {
    async seal(message) { return { ...message, ciphertext: 'sealed', signature: 'valid' }; },
    async verify(value) { return value.signature !== 'invalid'; },
    async unseal() { return JSON.stringify({ message_id: 'message-001', action: 'dashboard.refresh', payload: { accepted: true } }); }
  };
  const bus = options.bus || SGHV119Bus.create();
  bus.subscribe((message) => published.push(message));
  const runtime = SGHV119HawkingRuntime.create({
    channel,
    bus,
    now: () => 1700000000000,
    authorize: options.authorize || (async () => true),
    appendScar: (event) => scar.push(event),
    replayWindowMs: 60000,
    eventTarget: options.eventTarget
  });
  return { runtime, channel, bus, published, scar };
}

test('message factory requires immutable identity fields', () => {
  const message = SGHV119Message.create({ sender_id: 'owner', action: 'refresh', nonce: 'n', sequence: 1, payload: {} }, { messageId: 'm1' });
  assert.equal(message.message_id, 'm1');
  assert.throws(() => { message.message_id = 'changed'; }, TypeError);
});

test('malformed envelope is rejected and never published', async () => {
  const h = harness();
  await assert.rejects(() => h.runtime.receive(envelope({ message_id: undefined })), /invalid_envelope/);
  assert.equal(h.published.length, 0);
  assert.equal(h.scar.at(-1).event_type, 'HAWKING_MESSAGE_REJECTED');
});

test('invalid signature is rejected before authorization', async () => {
  let authorized = false;
  const h = harness({ authorize: async () => { authorized = true; return true; } });
  await assert.rejects(() => h.runtime.receive(envelope({ signature: 'invalid' })), /invalid_signature/);
  assert.equal(authorized, false);
});

test('authorization denial prevents decryption and publication', async () => {
  let decrypted = false;
  const h = harness({
    authorize: async () => false,
    channel: { async verify() { return true; }, async unseal() { decrypted = true; return '{}'; } }
  });
  await assert.rejects(() => h.runtime.receive(envelope()), /authorization_denied/);
  assert.equal(decrypted, false);
  assert.equal(h.published.length, 0);
});

test('replayed nonce is rejected', async () => {
  const h = harness();
  await h.runtime.receive(envelope());
  await assert.rejects(() => h.runtime.receive(envelope({ message_id: 'm2' })), /replay_detected/);
  assert.equal(h.published.length, 1);
});

test('sequence regression is rejected', async () => {
  const h = harness();
  await h.runtime.receive(envelope({ sequence: 2 }));
  await assert.rejects(() => h.runtime.receive(envelope({ message_id: 'm2', nonce: 'n2', sequence: 1 })), /sequence_regression/);
  assert.equal(h.published.length, 1);
});

test('SCAR is appended before publication', async () => {
  const order = [];
  const h = harness({
    bus: { subscribe() {}, publish() { order.push('publish'); }, close() {} }
  });
  h.runtime.options().appendScar = () => order.push('scar');
  // Use a fresh runtime so the injected order recorder is explicit.
  const runtime = SGHV119HawkingRuntime.create({
    channel: h.channel,
    bus: h.bus,
    now: () => 1700000000000,
    authorize: async () => true,
    appendScar: () => order.push('scar')
  });
  await runtime.receive(envelope());
  assert.deepEqual(order, ['scar', 'publish']);
});

test('accepted message is published once', async () => {
  const h = harness();
  await h.runtime.receive(envelope());
  assert.equal(h.published.length, 1);
});

test('decrypt failure is rejected without publication', async () => {
  const h = harness({ channel: { async verify() { return true; }, async unseal() { throw new Error('decrypt failed'); } } });
  await assert.rejects(() => h.runtime.receive(envelope()), /decrypt_failed/);
  assert.equal(h.published.length, 0);
});

test('close removes listener and revokes receive capability', async () => {
  const listeners = new Map();
  const eventTarget = {
    addEventListener(type, listener) { listeners.set(type, listener); },
    removeEventListener(type, listener) { if (listeners.get(type) === listener) listeners.delete(type); }
  };
  const h = harness({ eventTarget });
  assert.equal(listeners.has('sg:hawkingMsg'), true);
  h.runtime.close();
  assert.equal(listeners.has('sg:hawkingMsg'), false);
  assert.equal(h.runtime.isClosed(), true);
  await assert.rejects(() => h.runtime.receive(envelope()), /runtime_closed/);
});

test('SCAR never contains plaintext payload', async () => {
  const h = harness({ channel: { async verify() { return true; }, async unseal() { return JSON.stringify({ action: 'x', payload: { secret: 'private-value' } }); } } });
  await h.runtime.receive(envelope());
  const serialized = JSON.stringify(h.scar);
  assert.equal(serialized.includes('private-value'), false);
  assert.equal(serialized.includes('payload'), false);
});
