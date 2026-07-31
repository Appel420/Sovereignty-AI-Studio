#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const pkgPath = path.join(root, 'package.json');
const publicDir = path.join(root, 'public');
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

function fail(message) {
  console.error(`frontend validation failed: ${message}`);
  process.exitCode = 1;
}

if (!fs.existsSync(path.join(publicDir, 'index.html'))) fail('public/index.html is missing');
if (!fs.existsSync(path.join(publicDir, 'code-narration.js'))) fail('code narration parser is missing');
if (!fs.existsSync(path.join(publicDir, 'code-narration-ui.js'))) fail('code narration UI is missing');
if (!fs.existsSync(path.join(publicDir, 'device-family-tree.js'))) fail('device family-tree dashboard is missing');
if (!fs.existsSync(path.join(publicDir, 'device-family-tree.css'))) fail('device family-tree styles are missing');
if (pkg.sovereignty?.react !== false) fail('React must remain disabled');
if (Object.keys(pkg.dependencies || {}).length !== 0) fail('static frontend must have no runtime dependencies');

const index = fs.readFileSync(path.join(publicDir, 'index.html'), 'utf8');
const familyTree = fs.readFileSync(path.join(publicDir, 'device-family-tree.js'), 'utf8');
if (!index.includes('family-tree-panel')) fail('family-tree panel is not mounted');
if (!index.includes('device-family-tree.js')) fail('family-tree script is not loaded');
if (!familyTree.includes('network !== \'disabled\'')) fail('network boundary is not enforced');
if (!familyTree.includes('remote_recognition !== false')) fail('remote listening boundary is not enforced');
if (!familyTree.includes('NOT EVALUATED')) fail('authorization default is missing');
if (!familyTree.includes('LOCAL-ONLY / UNAVAILABLE')) fail('local SCAR fallback is missing');
if (familyTree.includes('http://') || familyTree.includes('https://')) fail('remote URL found in dashboard');

const context = { console, globalThis: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(publicDir, 'code-narration.js'), 'utf8'), context);
const api = context.globalThis.SovereignCodeNarration;
if (!api) fail('narration API did not initialize');
if (api.extractCodeBlocks('```python\ndef verify():\n    return True\n```').length !== 1) fail('Python extraction failed');
if (api.extractCodeBlocks('```javascript\nfunction verify() {}\n```')[0].language !== 'JavaScript') fail('JavaScript detection failed');
if (api.extractCodeBlocks('```typescript\ninterface Policy {}\n```')[0].language !== 'TypeScript') fail('TypeScript detection failed');
if (!api.containsCode('    def verify_state():\n        return False')) fail('indented-code detection failed');
const mixed = api.narrationText('The loader fails closed.\n```python\nreturn False\n```', 'explain-code');
if (mixed.includes('```') || !mixed.includes('text only')) fail('mixed narration failed');

if (!process.exitCode) console.log('static frontend validation passed');
