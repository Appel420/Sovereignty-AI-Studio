const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'runtime', 'devassist420-bridge.js'), 'utf8');
const calls = [];
const responses = [];

const context = {
  crypto: { randomUUID: () => 'test-request' },
  window: null,
  fetch: async (url, options) => {
    calls.push({ url, options });
    const next = responses.shift();
    return {
      ok: next.ok,
      json: async () => next.body,
    };
  },
};
context.window = context;
vm.runInNewContext(source, context);

(async () => {
  const api = context.SovereignDevAssist420;
  assert(api);

  const unauthenticated = await api.requestCapability({
    owner_authenticated: false,
    purpose: 'test',
    resource: { kind: 'model', id: 'grok-4-heavy', provider: 'xai', operation: 'model-load' },
  });
  assert.strictEqual(unauthenticated.state, 'REQUIRE_APPROVAL');
  assert.strictEqual(calls.length, 0);

  responses.push({ ok: true, body: {
    state: 'AUTHORIZED', capability_id: 'cap-test', session_id: 'sess-test', epoch: 17,
  }});
  const authorized = await api.requestCapability({
    owner_authenticated: true,
    purpose: 'test',
    resource: { kind: 'model', id: 'grok-4-heavy', provider: 'xai', operation: 'model-load' },
  });
  assert.strictEqual(authorized.state, 'AUTHORIZED');

  responses.push({ ok: true, body: { state: 'EXECUTED' } });
  const result = await api.executeAuthorized(authorized, {
    owner_authenticated: true,
    purpose: 'test',
    resource: { kind: 'model', id: 'grok-4-heavy', provider: 'xai', operation: 'model-load' },
  });
  assert.strictEqual(result.state, 'EXECUTED');
  assert.strictEqual(calls.length, 2);
  assert(calls[0].url.includes('/api/devassist420/authorize'));
  assert(calls[1].url.includes('/api/devassist420/execute'));

  await assert.rejects(
    () => api.executeAuthorized({ state: 'DENY' }, {}),
    /AUTHORIZED result/
  );

  console.log('test-devassist420-bridge: PASS');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
