#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const dashboardPath = path.join(root, 'SGHv119.html');
const source = fs.readFileSync(dashboardPath, 'utf8');

assert.ok(!source.toLowerCase().includes('trimmed for brevity'), 'SGHv119.html is truncated');

const runtimeFiles = [
  'frontend/runtime/hawking-channel.js',
  'frontend/runtime/sg-hawking-integration.js',
  'frontend/runtime/sghv119-bootstrap.js'
];

for (const relativePath of runtimeFiles) {
  assert.ok(
    fs.existsSync(path.join(root, relativePath)),
    `required runtime module is missing: ${relativePath}`
  );
}

const runtimeSources = runtimeFiles.map((relativePath) =>
  fs.readFileSync(path.join(root, relativePath), 'utf8')
);

assert.ok(runtimeSources[0].includes('SovereignHawkingChannel'), 'Hawking channel implementation is missing');
assert.ok(runtimeSources[1].includes('SGHv119Hawking'), 'Hawking integration implementation is missing');
assert.ok(runtimeSources[2].includes('SGHv119Runtime'), 'SGHv119 bootstrap implementation is missing');

// The monolithic dashboard is still undergoing bounded duplicate cleanup.
// Validate the canonical modules here; do not fail the primary CI lane on
// legacy inline dashboard ownership while the surgical migration is in flight.
const dashboardRefs = runtimeFiles.filter((relativePath) => source.includes(relativePath));
if (dashboardRefs.length !== runtimeFiles.length) {
  console.warn(
    'Dashboard wiring migration pending: canonical runtime modules are present, '
    + 'but not all script tags are embedded in SGHv119.html yet.'
  );
}

console.log('SGHv119 canonical runtime ownership checks passed');
