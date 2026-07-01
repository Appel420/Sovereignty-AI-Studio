'use strict';

/**
 * Node.js counterpart for crypto/e2ee_quad_ratchet.js.
 * Uses node:crypto WebCrypto so the bridge can process SGHV119 encrypted envelopes.
 */

const { webcrypto } = require('node:crypto');

const SGHV119_QR_VERSION = 'SGHV119-E2EE-QR-v1';
const subtle = webcrypto.subtle;

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
  return Buffer.from(bytes).toString('base64');
}

function fromB64(value) {
  return new Uint8Array(Buffer.from(value, 'base64'));
}

function randomBytes(length) {
  const out = new Uint8Array(length);
  webcrypto.getRandomValues(out);
  return out;
}

async function importHkdfKey(raw) {
  return subtle.importKey('raw', raw, 'HKDF', false, ['deriveBits']);
}

async function hkdf(rawKey, salt, info, lengthBytes = 32) {
  const key = await importHkdfKey(rawKey);
  const bits = await subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt, info: utf8(info) },
    key,
    lengthBytes * 8,
  );
  return new Uint8Array(bits);
}

async function aesKey(raw) {
  return subtle.importKey('raw', raw, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}

async function sha256(bytes) {
  return new Uint8Array(await subtle.digest('SHA-256', bytes));
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

async function deriveBootstrapRoot(secret) {
  if (!secret || String(secret).length < 32) {
    throw new Error('SGHV119_E2EE_BOOTSTRAP_SECRET must be at least 32 characters');
  }
  return sha256(utf8('SGHV119 bootstrap:' + String(secret)));
}

function createInitialState(options) {
  const rootKey = options.rootKeyBytes || randomBytes(32);
  return {
    version: SGHV119_QR_VERSION,
    sessionId: options.sessionId,
    epoch: 0,
    sendCounter: 0,
    receiveCounter: 0,
    rootKeyB64: b64(rootKey),
  };
}

async function serverStateForEnvelope(envelope, bootstrapSecret) {
  if (!envelope || !envelope.meta || !envelope.meta.sessionId) {
    throw new Error('Missing E2EE envelope session');
  }
  const rootKeyBytes = await deriveBootstrapRoot(bootstrapSecret);
  return createInitialState({ sessionId: envelope.meta.sessionId, rootKeyBytes });
}

async function decryptClientEnvelope(state, envelope) {
  if (!envelope || envelope.version !== SGHV119_QR_VERSION) {
    throw new Error('Unsupported E2EE envelope version');
  }
  const rootKey = fromB64(state.rootKeyB64);
  const epochKeys = await deriveEpoch(rootKey, envelope.meta.epoch);
  const counter = envelope.meta.counter;
  const chain = await nextChainKey(epochKeys.send, 'send', counter);
  const msgKey = await messageKey(chain, 'send', counter);
  const ciphertext = fromB64(envelope.ciphertext);
  const expected = await headerTag(epochKeys.header, envelope.meta, ciphertext);
  if (expected !== envelope.headerTag) {
    throw new Error('Header ratchet authentication failed');
  }
  const plain = await subtle.decrypt(
    { name: 'AES-GCM', iv: fromB64(envelope.nonce), additionalData: aad(envelope.meta), tagLength: 128 },
    await aesKey(msgKey),
    ciphertext,
  );
  state.receiveCounter = Math.max(state.receiveCounter, counter);
  state.rootKeyB64 = b64(epochKeys.root);
  return JSON.parse(new TextDecoder().decode(plain));
}

async function encryptServerEnvelope(state, plaintextObject, routeMeta) {
  const rootKey = fromB64(state.rootKeyB64);
  const epochKeys = await deriveEpoch(rootKey, state.epoch);
  const counter = state.sendCounter + 1;
  const chain = await nextChainKey(epochKeys.recv, 'receive', counter);
  const msgKey = await messageKey(chain, 'receive', counter);
  const nonce = randomBytes(12);
  const meta = {
    sessionId: state.sessionId,
    epoch: state.epoch,
    counter,
    direction: 'inbound',
    agent: routeMeta.agent,
    branch: routeMeta.branch,
    route: routeMeta.route || '/ai/' + routeMeta.agent,
  };
  const plaintext = utf8(JSON.stringify(plaintextObject));
  const cipher = new Uint8Array(await subtle.encrypt(
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

module.exports = {
  version: SGHV119_QR_VERSION,
  deriveBootstrapRoot,
  serverStateForEnvelope,
  decryptClientEnvelope,
  encryptServerEnvelope,
};
