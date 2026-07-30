// src/audit.js
// Append-only, hash-chained audit log. Each entry's hash covers its own
// fields + the previous entry's hash, so any retroactive edit breaks the chain.

const crypto = require('crypto');
const db = require('./db');

function lastHash() {
  const row = db.prepare('SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1').get();
  return row ? row.hash : 'GENESIS';
}

function record({ actor = 'system', action, entity_type = null, entity_id = null, payload = null }) {
  const ts = new Date().toISOString();
  const prev_hash = lastHash();
  const payloadStr = payload ? JSON.stringify(payload) : null;
  // Hash over the STORED string form of payload, so record() and verifyChain()
  // are hashing identical bytes rather than an object vs. its string re-encoding.
  const body = JSON.stringify({ ts, actor, action, entity_type, entity_id, payload: payloadStr, prev_hash });
  const hash = crypto.createHash('sha256').update(body).digest('hex');

  db.prepare(`
    INSERT INTO audit_log (ts, actor, action, entity_type, entity_id, payload, prev_hash, hash)
    VALUES (@ts, @actor, @action, @entity_type, @entity_id, @payload, @prev_hash, @hash)
  `).run({
    ts, actor, action, entity_type, entity_id,
    payload: payloadStr,
    prev_hash, hash
  });

  return hash;
}

// Verifies the whole chain is intact - run periodically or on demand via /api/audit/verify
function verifyChain() {
  const rows = db.prepare('SELECT * FROM audit_log ORDER BY id ASC').all();
  let prev = 'GENESIS';
  for (const row of rows) {
    const body = JSON.stringify({
      ts: row.ts, actor: row.actor, action: row.action,
      entity_type: row.entity_type, entity_id: row.entity_id,
      payload: row.payload, prev_hash: prev
    });
    const expected = crypto.createHash('sha256').update(body).digest('hex');
    if (row.prev_hash !== prev || row.hash !== expected) {
      return { valid: false, brokenAt: row.id };
    }
    prev = row.hash;
  }
  return { valid: true, entries: rows.length };
}

module.exports = { record, verifyChain };
