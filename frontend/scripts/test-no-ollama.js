'use strict';

const fs = require('fs');
const assert = require('assert');

const activeProvider = fs.readFileSync('backend/api/providers/index.js', 'utf8').toLowerCase();
assert.ok(!activeProvider.includes('11434'), 'active provider map references a forbidden legacy port');
assert.ok(!activeProvider.includes('ollama'), 'active provider map references a disabled provider');
assert.ok(!activeProvider.includes('localmodel'), 'disabled local provider is still registered');
assert.ok(!activeProvider.includes('local:'), 'disabled local provider map entry remains');

const disabledProvider = fs.readFileSync('backend/api/providers/local.js', 'utf8');
assert.ok(disabledProvider.includes('Local provider is unavailable'), 'local provider is not fail-closed');

console.log('provider boundary check passed');
