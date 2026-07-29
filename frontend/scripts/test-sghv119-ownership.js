#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const dashboardPath = path.join(root, 'SGHv119.html');
const source = fs.readFileSync(dashboardPath, 'utf8');

assert.ok(!source.toLowerCase().includes('trimmed for brevity'), 'SGHv119.html is truncated');
assert.strictEqual(
  (source.match(/frontend\/runtime\/hawking-channel\.js/g) || []).length,
  1,
  'Hawking channel must be loaded exactly once'
);
assert.strictEqual(
  (source.match(/frontend\/runtime\/sg-hawking-integration\.js/g) || []).length,
  1,
  'Hawking integration must be loaded exactly once'
);
assert.strictEqual(
  (source.match(/frontend\/runtime\/sghv119-bootstrap\.js/g) || []).length,
  1,
  'SGHv119 bootstrap must be loaded exactly once'
);
assert.strictEqual(
  (source.match(/SovereignHawkingChannel\s*=|SovereignHawkingChannel\s*\(/g) || []).length,
  0,
  'inline Hawking manager must not remain in the dashboard'
);
assert.strictEqual(
  (source.match(/_SG_BRIDGE_STATUS\s*=|BRIDGE STATUS SINGLETON/g) || []).length,
  0,
  'inline bridge singleton must not remain in the dashboard'
);
assert.strictEqual(
  (source.match(/Blocked in local\/offline mode/g) || []).length,
  0,
  'local mode must not block approved loopback transport'
);
assert.strictEqual(
  (source.match(/new\s+WebSocket\s*\(|WebSocket\s*=\s*function/g) || []).length,
  0,
  'duplicate inline WebSocket manager must not remain in the dashboard'
);

console.log('SGHv119 HTML ownership checks passed');
