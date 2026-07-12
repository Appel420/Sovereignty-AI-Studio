'use strict';

/**
 * SGHV119 E2EE Quad Ratchet Envelope
 *
 * Purpose:
 * - HTTP-safe encrypted envelope for SGHV119 -> bridge -> agent traffic.
 * - No browser ws:// dependency.
 * - Uses WebCrypto in browsers and Node 20+ globalThis.crypto.subtle.
 *
 * Ratchets:
 * 1. Root ratchet: updates root key per epoch.
 * 2. Send chain ratchet: derives outbound message keys.
 * 3. Receive chain ratchet: derives inbound message keys.
 * 4. Header/audit ratchet: authenticates metadata without exposing plaintext.
 *
 * Current primitive set:
 * - HKDF-SHA-256
 * - AES-256-GCM
 * - 96-bit nonces
 * - Additional authenticated data bound to session, branch, agent, counter, and epoch
 *
 * Important:
 * This is a symmetric envelope layer. Production deployment should add an
 * authenticated X25519 or PQ/hybrid KEM handshake to establish the initial root
 * key. Until then, never hardcode or commit root keys.
 */

const SGHV119_QR_VERSION = 'SGHV119-E2EE-QR-v1';

function getCrypto() {
  const c = globalThis.crypto;
  if (!c || !c.subtle) {
    throw new Error('WebCrypto subtle API is required');
  }
  return c;
}

function utf8(value) {
  return new TextEncoder().encode(String(value));
}

function concatBytes(...parts) {
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const p of parts) {
    out.set(p, offset);
    offset += p.length;
  }
  return out;
}

function b64(bytes) {
  if (typeof Buffer !== 'undefined') return Buffer.from(bytes).toString('base64');
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function fromB64(value) {
  if (typeof Buffer !== 'undefined') return new Uint8Array(Buffer.from(value, 'base64'));
  const bin = atob(value);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function randomBytes(length) {
  const out = new Uint8Array(length);
  getCrypto().getRandomValues(out);
  return out;
}

async function importHkdfKey(raw) {
  return getCrypto().subtle.importKey('raw', raw, 'HKDF', false, ['deriveBits']);
}

async function hkdf(rawKey, salt, info, lengthBytes = 32) {
  const key = await importHkdfKey(rawKey);
  const bits = await getCrypto().subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt, info: utf8(info) },
    key,
    lengthBytes * 8,
  );
  return new Uint8Array(bits);
}

async function aesKey(raw) {
  return getCrypto().subtle.importKey('raw', raw, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}

async function sha256(bytes) {
  return new Uint8Array(await getCrypto().subtle.digest('SHA-256', bytes));
}

function aad(meta) {
  return utf8(JSON.stringify({
    v: SGHV119_QR_VERSION,
    sessionId: meta.sessionId,
    epoch: meta.epoch,
    counter: meta.counter,
    direction: meta.direction,
    agent: meta.agent,
    branch: meta.branch,
    route: meta.route,
  }));
}

async function deriveEpoch(rootKey, epoch) {
  const salt = utf8('sghv119:quad-ratchet:epoch:' + epoch);
  const root = await hkdf(rootKey, salt, 'root-ratchet', 32);
  const send = await hkdf(root, salt, 'send-chain', 32);
  const recv = await hkdf(root, salt, 'receive-chain', 32);
  const header = await hkdf(root, salt, 'header-audit-chain', 32);
  return { root, send, recv, header };
}

async function nextChainKey(chainKey, label, counter) {
  return hkdf(chainKey, utf8('sghv119:' + label + ':' + counter), 'chain-step', 32);
}

async function messageKey(chainKey, label, counter) {
  return hkdf(chainKey, utf8('sghv119:message:' + label + ':' + counter), 'message-key', 32);
}

async function headerTag(headerKey, meta, ciphertext) {
  return b64(await sha256(concatBytes(headerKey, aad(meta), ciphertext)));
}

function createInitialState(options) {
  const rootKey = options.rootKeyBytes || randomBytes(32);
  return {
    version: SGHV119_QR_VERSION,
    sessionId: options.sessionId || b64(randomBytes(16)),
    epoch: 0,
    sendCounter: 0,
    receiveCounter: 0,
    rootKeyB64: b64(rootKey),
  };
}

async function encryptEnvelope(state, plaintextObject, routeMeta) {
  const rootKey = fromB64(state.rootKeyB64);
  const epochKeys = await deriveEpoch(rootKey, state.epoch);
  const counter = state.sendCounter + 1;
  const chain = await nextChainKey(epochKeys.send, 'send', counter);
  const msgKey = await messageKey(chain, 'send', counter);
  const nonce = randomBytes(12);
  const meta = {
    sessionId: state.sessionId,
    epoch: state.epoch,
    counter,
    direction: 'outbound',
    agent: routeMeta.agent,
    branch: routeMeta.branch,
    route: routeMeta.route || '/ai/' + routeMeta.agent,
  };
  const plaintext = utf8(JSON.stringify(plaintextObject));
  const cipher = new Uint8Array(await getCrypto().subtle.encrypt(
    { name: 'AES-GCM', iv: nonce, additionalData: aad(meta), tagLength: 128 },
    await aesKey(msgKey),
    plaintext,
  ));
  const tag = await headerTag(epochKeys.header, meta, cipher);
  state.sendCounter = counter;
  state.rootKeyB64 = b64(epochKeys.root);
  return {
    version: SGHV119_QR_VERSION,
    meta,
    nonce: b64(nonce),
    ciphertext: b64(cipher),
    headerTag: tag,
  };
}

async function decryptEnvelope(state, envelope) {
  if (!envelope || envelope.version !== SGHV119_QR_VERSION) {
    throw new Error('Unsupported E2EE envelope version');
  }
  const rootKey = fromB64(state.rootKeyB64);
  const epochKeys = await deriveEpoch(rootKey, envelope.meta.epoch);
  const counter = envelope.meta.counter;
  const chain = await nextChainKey(epochKeys.recv, 'receive', counter);
  const msgKey = await messageKey(chain, 'receive', counter);
  const ciphertext = fromB64(envelope.ciphertext);
  const expected = await headerTag(epochKeys.header, envelope.meta, ciphertext);
  if (expected !== envelope.headerTag) {
    throw new Error('Header ratchet authentication failed');
  }
  const plain = await getCrypto().subtle.decrypt(
    { name: 'AES-GCM', iv: fromB64(envelope.nonce), additionalData: aad(envelope.meta), tagLength: 128 },
    await aesKey(msgKey),
    ciphertext,
  );
  state.receiveCounter = Math.max(state.receiveCounter, counter);
  state.rootKeyB64 = b64(epochKeys.root);
  return JSON.parse(new TextDecoder().decode(plain));
}

const SGHV119QuadRatchet = {
  version: SGHV119_QR_VERSION,
  createInitialState,
  encryptEnvelope,
  decryptEnvelope,
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = SGHV119QuadRatchet;
}

if (typeof window !== 'undefined') {
  window.SGHV119QuadRatchet = SGHV119QuadRatchet;
}
