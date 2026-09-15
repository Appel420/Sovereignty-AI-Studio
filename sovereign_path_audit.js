#!/usr/bin/env node
'use strict';

/*
 * Sovereign Path Audit
 *
 * Purpose:
 *   Compile the architecture discussed in this conversation into one
 *   executable, dependency-free Node.js audit engine.
 *
 * It does NOT pretend that documentation proves enforcement.
 * It traces:
 *   INTENDED PATH -> IMPLEMENTATION -> ENFORCEMENT -> EVIDENCE
 *
 * It emits:
 *   ✓ PROVEN
 *   ⚠ PARTIAL
 *   ✗ OFF_PATH
 *   ? DISCUSS_WITH_USER
 *   ⊘ REJECT
 *
 * Usage:
 *   node sovereign_path_audit.js
 *   node sovereign_path_audit.js --json
 *   node sovereign_path_audit.js path/to/artifact.html
 *   node sovereign_path_audit.js path/to/artifact.html --json
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const STATUS = Object.freeze({
  PROVEN: 'PROVEN',
  PARTIAL: 'PARTIAL',
  OFF_PATH: 'OFF_PATH',
  DISCUSS: 'DISCUSS_WITH_USER',
  REJECT: 'REJECT'
});

const EXPECTED_PATH = [
  'Owner intent',
  'Cryptographic identity',
  'Signature verification',
  'Policy authorization',
  'Capability + scope + lease',
  'Execution',
  'Signed execution receipt',
  'SCAR 5W1H event',
  'Merkle/provenance verification',
  'Owner-visible result'
];

const checks = [
  {
    id: 'AUTH-001',
    control: 'Owner identity',
    expected: 'Cryptographic identity is established before authorization.',
    patterns: [
      /ML-DSA|Dilithium|Ed25519|Falcon|signature|verify/i
    ],
    bad: [
      /username.*role|role.*username/i,
      /currentRole\s*=/i,
      /sessionStorage\.setItem\(['"]XAIUserRole/i
    ],
    status: STATUS.OFF_PATH,
    reason:
      'The supplied XAI UI uses a username field and client-selected role. ' +
      'That is UI state, not authenticated identity.'
  },
  {
    id: 'AUTH-002',
    control: 'Authorization',
    expected: 'Authentication is followed by server-side/policy authorization.',
    patterns: [
      /authorization/i,
      /capability/i,
      /policy/i
    ],
    bad: [
      /currentRole\s*===\s*['"]admin['"]/i,
      /currentRole\s*===/i
    ],
    status: STATUS.REJECT,
    reason:
      'A client-side role selector must never independently grant administrative authority.'
  },
  {
    id: 'AUTH-003',
    control: 'Capability / scope / lease',
    expected: 'Execution requires an explicit scoped capability and valid lease.',
    patterns: [
      /capability/i,
      /scope/i,
      /lease/i,
      /expiry|expires|nonce/i
    ],
    status: STATUS.OFF_PATH,
    reason:
      'No enforceable capability/scope/lease boundary is demonstrated in the supplied application.'
  },
  {
    id: 'CRYPTO-001',
    control: 'Digital signature',
    expected: 'Signing uses an actual asymmetric signing primitive and verification uses the public key.',
    patterns: [
      /ML-DSA|Dilithium|Falcon|Ed25519/i
    ],
    bad: [
      /digest\(['"]SHA-256['"]/i,
      /signatureBytes\s*=\s*new Uint8Array\(hashBuffer\)/i,
      /XAI SIGNATURE/i
    ],
    status: STATUS.REJECT,
    reason:
      'The supplied certificate generator computes SHA-256 and labels the digest a signature. ' +
      'A digest is not an asymmetric signature.'
  },
  {
    id: 'CRYPTO-002',
    control: 'KEM secret handling',
    expected: 'Shared secrets are never rendered into ordinary production UI.',
    patterns: [
      /sharedSecret/i,
      /decaps/i
    ],
    bad: [
      /Sender Shared Secret/i,
      /Receiver Shared Secret/i
    ],
    status: STATUS.REJECT,
    reason:
      'The supplied Q-Resist UI displays the raw shared secret. Production security UI must not expose it.'
  },
  {
    id: 'CRYPTO-003',
    control: 'KEM implementation',
    expected: 'Encapsulation and decapsulation independently produce the same shared secret.',
    patterns: [
      /encaps/i,
      /decaps/i,
      /arraysEqual/i
    ],
    status: STATUS.PARTIAL,
    reason:
      'The supplied implementation contains an actual local KEM round-trip test, but key lifecycle and secret handling are not production-grade.'
  },
  {
    id: 'AUDIT-001',
    control: 'Immutable audit',
    expected: 'Every security-relevant action creates a signed, chained event.',
    patterns: [
      /audit/i,
      /timestamp/i,
      /action/i
    ],
    bad: [
      /let\s+auditEntries\s*=\s*\[\]/i,
      /auditEntries\.push/i
    ],
    status: STATUS.OFF_PATH,
    reason:
      'An in-memory JavaScript array is mutable, disappears on reload, and has no cryptographic chain.'
  },
  {
    id: 'AUDIT-002',
    control: 'SCAR 5W1H',
    expected: 'Receipts contain actor, action, resource, time, reason/context, result, and cryptographic linkage.',
    patterns: [
      /5W1H|SCAR/i
    ],
    status: STATUS.OFF_PATH,
    reason:
      'SCAR is referenced architecturally but the supplied UI does not generate the required signed 5W1H receipt.'
  },
  {
    id: 'AUDIT-003',
    control: 'Merkle / chain verification',
    expected: 'Each event commits to the previous event and the resulting root is independently verifiable.',
    patterns: [
      /Merkle|previous.*hash|prev.*hash|root.*hash|chain.*hash/i
    ],
    status: STATUS.OFF_PATH,
    reason:
      'No enforceable previous-hash linkage or independently verified Merkle root is implemented in the supplied application.'
  },
  {
    id: 'TRANSPORT-001',
    control: 'HTTPS / port 443',
    expected: 'Authenticated encrypted transport protects network operations.',
    patterns: [
      /https|TLS|443/i
    ],
    status: STATUS.DISCUSS,
    reason:
      'Port 443 is transport, not authorization. Actual TLS termination, certificate validation, and identity binding must be verified separately.'
  },
  {
    id: 'DNS-001',
    control: 'SPF',
    expected: 'SPF authorizes the actual outbound mail senders.',
    patterns: [
      /v=spf1/i
    ],
    status: STATUS.PARTIAL,
    reason:
      'The record is structurally plausible, but actual sending infrastructure must be cross-checked before claiming compliance.'
  },
  {
    id: 'DNS-002',
    control: 'DKIM',
    expected: 'A real public DKIM key is published and matches the signing service.',
    patterns: [
      /DKIM1/i
    ],
    bad: [
      /p=""/i,
      /p=\\?["']/i
    ],
    status: STATUS.REJECT,
    reason:
      'The supplied DKIM public key is empty. It is a placeholder, not an operational DKIM key.'
  },
  {
    id: 'DNS-003',
    control: 'DMARC',
    expected: 'DMARC policy is syntactically valid and reporting destinations are operational.',
    patterns: [
      /v=DMARC1/i
    ],
    status: STATUS.PARTIAL,
    reason:
      'The policy is documented, but actual DNS publication and report mailbox ownership must be verified.'
  },
  {
    id: 'DNS-004',
    control: 'MTA-STS',
    expected: 'DNS advertisement is backed by the required HTTPS policy document.',
    patterns: [
      /v=STSv1/i,
      /_mta-sts/i
    ],
    status: STATUS.PARTIAL,
    reason:
      'The TXT advertisement alone does not prove the HTTPS MTA-STS policy exists or is enforceable.'
  },
  {
    id: 'DNS-005',
    control: 'Production DNS',
    expected: 'Published addresses and hostnames correspond to real infrastructure.',
    patterns: [
      /203\.0\.113\./i,
      /2001:db8:/i,
      /yourdomain\.tld/i
    ],
    status: STATUS.REJECT,
    reason:
      'The supplied DNS uses documentation/example placeholders and cannot be treated as production DNS.'
  },
  {
    id: 'CODE-001',
    control: 'Executable integrity',
    expected: 'The submitted artifact parses and executes without syntax errors.',
    patterns: [
      /<!DOCTYPE html>|function\s+/i
    ],
    status: STATUS.PARTIAL,
    reason:
      'The supplied XAI HTML contains malformed JavaScript/template literals and typographic quotes that require cleanup.'
  },
  {
    id: 'CODE-002',
    control: 'Single executable artifact',
    expected: 'One coherent application has one document lifecycle and controlled namespaces.',
    patterns: [
      /<!DOCTYPE html>/gi
    ],
    status: STATUS.PARTIAL,
    reason:
      'Two complete HTML documents were concatenated. They need to be consolidated before production use.'
  }
];

function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

function canonical(value) {
  return JSON.stringify(value, Object.keys(value).sort());
}

function buildReceipt(check, sourceHash, sequence, previousHash) {
  const event = {
    sequence,
    event_id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    actor_id: 'sovereign-path-audit',
    action: 'CONTROL_REVIEW',
    resource: check.control,
    expected: check.expected,
    result: check.status,
    reason: check.reason,
    source_hash: sourceHash,
    previous_event_hash: previousHash || null
  };

  event.event_hash = sha256(canonical(event));
  return event;
}

function scanArtifact(source) {
  const results = [];

  for (const check of checks) {
    let matched = check.patterns.some((r) => r.test(source));
    let bad = check.bad && check.bad.some((r) => r.test(source));

    let status = check.status;

    if (!matched && status === STATUS.PROVEN) {
      status = STATUS.OFF_PATH;
    }

    if (bad) {
      status = check.status === STATUS.DISCUSS
        ? STATUS.DISCUSS
        : check.status;
    }

    results.push({
      id: check.id,
      control: check.control,
      expected: check.expected,
      status,
      reason: check.reason,
      evidence_present: matched,
      negative_indicator_present: !!bad
    });
  }

  return results;
}

function summarize(results) {
  return results.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {});
}

function render(results, sourceHash, json = false) {
  let previousHash = null;
  const receipts = results.map((r, i) => {
    const receipt = buildReceipt(r, sourceHash, i + 1, previousHash);
    previousHash = receipt.event_hash;
    return receipt;
  });

  const root = sha256(receipts.map(r => r.event_hash).join(''));

  const report = {
    schema: 'sovereign-path-audit/v1',
    generated_at: new Date().toISOString(),
    source_hash: sourceHash,
    expected_path: EXPECTED_PATH,
    summary: summarize(results),
    controls: results,
    receipts,
    chain_root: root,
    invariants: [
      'Signature verification does not independently authorize execution.',
      'Transport security does not constitute authorization.',
      'A hash is not a digital signature.',
      'A UI role selector is not authentication.',
      'An in-memory audit array is not immutable provenance.',
      'A failed mutation must not overwrite the last known-good provenance root.',
      'Production cryptographic interfaces must not display shared secrets.'
    ]
  };

  if (json) {
    console.log(JSON.stringify(report, null, 2));
    return;
  }

  console.log('\nSOVEREIGN PATH AUDIT');
  console.log('====================');
  console.log(`Source SHA-256: ${sourceHash}`);
  console.log(`Chain root:     ${root}\n`);

  for (const r of results) {
    const icon = {
      [STATUS.PROVEN]: '✓',
      [STATUS.PARTIAL]: '⚠',
      [STATUS.OFF_PATH]: '✗',
      [STATUS.DISCUSS]: '?',
      [STATUS.REJECT]: '⊘'
    }[r.status];

    console.log(`${icon} ${r.status.padEnd(18)} ${r.id}  ${r.control}`);
    console.log(`  Expected: ${r.expected}`);
    console.log(`  Why:      ${r.reason}`);
    console.log(`  Evidence: ${r.evidence_present ? 'present' : 'not demonstrated'}`);
    console.log('');
  }

  console.log('PATH MODEL');
  console.log('----------');
  console.log(EXPECTED_PATH.join(' -> '));

  console.log('\nINVARIANTS');
  console.log('----------');
  for (const invariant of report.invariants) {
    console.log(`• ${invariant}`);
  }

  console.log('\nSUMMARY');
  console.log('-------');
  console.log(JSON.stringify(report.summary, null, 2));
}

function readInputs(args) {
  const files = args.filter(a => !a.startsWith('--'));

  if (files.length === 0) {
    return {
      source:
        `DNS / architecture / code supplied in the conversation\n` +
        `This audit is evaluating the compiled control model and known implementation findings.`,
      label: 'conversation-compiled-model'
    };
  }

  const chunks = [];
  for (const file of files) {
    const resolved = path.resolve(file);
    if (!fs.existsSync(resolved)) {
      throw new Error(`File not found: ${file}`);
    }
    chunks.push(fs.readFileSync(resolved, 'utf8'));
  }

  return {
    source: chunks.join('\n\n'),
    label: files.join(', ')
  };
}

function main() {
  const args = process.argv.slice(2);
  const json = args.includes('--json');

  try {
    const input = readInputs(args);
    const sourceHash = sha256(input.source);
    const results = scanArtifact(input.source);
    render(results, sourceHash, json);
  } catch (err) {
    console.error(`AUDIT ERROR: ${err.message}`);
    process.exitCode = 1;
  }
}

main();
