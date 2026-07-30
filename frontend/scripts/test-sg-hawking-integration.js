'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const channelSource = fs.readFileSync(path.join(__dirname, '..', 'runtime', 'hawking-channel.js'), 'utf8');
const integrationSource = fs.readFileSync(path.join(__dirname, '..', 'runtime', 'sg-hawking-integration.js'), 'utf8');
const context = {
  globalThis: {},
  crypto: require('crypto').webcrypto,
  document: { dispatchEvent() {} },
  CustomEvent: function (name, init) { this.type = name; this.detail = init.detail; },
  btoa: value => Buffer.from(value, 'binary').toString('base64'),
  atob: value => Buffer.from(value, 'base64').toString('binary'),
  TextEncoder,
  TextDecoder,
  Set,
  URL
};
vm.createContext(context);
vm.runInContext(channelSource, context);
vm.runInContext(integrationSource, context);

assert.ok(context.globalThis.SGHv119Hawking);
const channel = context.globalThis.SovereignHawkingChannel.create({
  crypto: context.crypto,
  eventTarget: context.document,
  CustomEvent: context.CustomEvent
});
const integration = context.globalThis.SGHv119Hawking.create({
  channel,
  trustedFingerprints: []
});

(async () => {
  await integration.init();
  const envelope = await channel.seal('integration test');
  assert.strictEqual(integration.authorizeEnvelope(envelope), false);
  await assert.rejects(() => integration.receive(envelope), /not trusted/);

  integration.setTrustedFingerprints([envelope.fingerprint]);
  assert.strictEqual(integration.authorizeEnvelope(envelope), true);
  assert.strictEqual(await integration.receive(envelope), 'integration test');
  console.log('SGHv119 Hawking integration and fingerprint policy tests passed');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
