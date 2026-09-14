// sovereign_path_audit.js
// Restored during live cleanup. Tracks path integrity for Sovereignty-AI-Studio.
// Generated: 2026-09-14T11:01:00Z
// Owner: Appel420

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const AUDIT_LOG = path.join(process.cwd(), 'sovereign_audit.jsonl');

function hashPath(p) {
  return crypto.createHash('sha256').update(p).digest('hex');
}

function auditEntry(event, detail) {
  const entry = {
    ts: new Date().toISOString(),
    event,
    detail,
    pathHash: hashPath(detail || ''),
  };
  fs.appendFileSync(AUDIT_LOG, JSON.stringify(entry) + '\n');
  return entry;
}

module.exports = { hashPath, auditEntry, AUDIT_LOG };
