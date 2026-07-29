'use strict';

const fs = require('fs');
const vm = require('vm');
const path = require('path');
const assert = require('assert');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'public', 'voice-confirmation.js'),
  'utf8'
);

const context = { globalThis: {} };
vm.createContext(context);
vm.runInContext(source, context);

const api = context.globalThis.SovereignVoiceConfirmation;
assert.ok(api, 'voice confirmation API did not initialize');

let result = api.analyze({
  transcript: 'run pie',
  confidence: 0.71
});
assert.strictEqual(result.level, 'review');
assert.strictEqual(result.needsConfirmation, true);
assert.strictEqual(result.candidates[0].canonical, 'pytest');

result = api.analyze({
  transcript: 'push this to main',
  confidence: 0.98
});
assert.strictEqual(result.level, 'required');
assert.strictEqual(result.needsConfirmation, true);
assert.deepStrictEqual(Array.from(result.riskTerms), ['push', 'main']);

result = api.analyze({
  transcript: 'use feature canonical governance core',
  confidence: 0.98
});
assert.strictEqual(result.level, 'review');
assert.strictEqual(result.needsConfirmation, true);
assert.ok(result.repositoryTerms.includes('canonical governance core'));
assert.strictEqual(result.candidates[0].canonical, 'feature/canonical-governance-core');

result = api.analyze({
  transcript: 'sign the image with co sign on ghcr',
  confidence: 0.98
});
assert.strictEqual(result.level, 'blocked');
assert.strictEqual(result.blocked, true);
assert.strictEqual(result.needsConfirmation, false);
assert.ok(result.repositoryTerms.includes('co sign'));
assert.ok(result.repositoryTerms.includes('ghcr'));

result = api.analyze({
  transcript: 'start hyper corn locally',
  confidence: 0.98
});
assert.strictEqual(result.level, 'required');
assert.strictEqual(result.needsConfirmation, true);
assert.strictEqual(result.candidates[0].canonical, 'hypercorn');

result = api.analyze({
  transcript: 'show me the branch status',
  confidence: 0.96
});
assert.strictEqual(result.level, 'required');
assert.strictEqual(result.needsConfirmation, true);

const blockedReadBack = api.readBack(api.analyze({
  transcript: 'push this to ghcr',
  confidence: 0.99
}));
assert.ok(blockedReadBack.includes('local-first policy'));

console.log('local voice confirmation tests passed');
