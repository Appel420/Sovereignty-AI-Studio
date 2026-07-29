'use strict';

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
assert.ok(context.globalThis.SovereignHawkingChannel);
assert.strictEqual(
  context.globalThis.SovereignHawkingChannel.STATUS.READY,
  'READY'
);

const channel = context.globalThis.SovereignHawkingChannel.create({ eventTarget });
assert.strictEqual(channel.getStatus(), 'INIT');
assert.strictEqual(channel.getFingerprint(), null);

console.log('Hawking channel contract loaded; WebCrypto integration is tested in browser runtime');
