'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync(path.join(__dirname, '..', 'runtime', 'sghv119-bootstrap.js'), 'utf8');
const calls = [];
const status = { id: 'sgb-hawking' };
const document = {
  readyState: 'complete',
  body: { appendChild(node) { calls.push(['body', node.id]); } },
  getElementById(id) { return id === 'sgb-hawking' ? status : null; },
  addEventListener() {}
};
const runtime = { init() { calls.push(['init']); return Promise.resolve(); } };
const context = {
  globalThis: {},
  document,
  console,
  SG_TRUSTED_FINGERPRINTS: [],
  SGHv119Hawking: {
    create(options) {
      assert.strictEqual(options.statusElement, status);
      assert.deepStrictEqual(options.trustedFingerprints, []);
      calls.push(['create']);
      return runtime;
    }
  }
};
vm.createContext(context);
vm.runInContext(source, context);
assert.strictEqual(context.globalThis.SGHv119Runtime.bootHawking, context.globalThis.SGHv119Runtime.bootHawking);
assert.strictEqual(calls[0][0], 'create');
assert.strictEqual(calls[1][0], 'init');
assert.strictEqual(context.globalThis.SGHv119HawkingRuntime, runtime);

console.log('SGHv119 bootstrap tests passed');
