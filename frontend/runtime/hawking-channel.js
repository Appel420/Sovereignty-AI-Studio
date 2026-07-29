/*
 * Sovereign Hawking Channel
 *
 * Local-first encrypted message channel for SGHv119 integration.
 *
 * The browser implementation uses WebCrypto P-256 ECDH and ECDSA because these
 * are broadly available in browser WebCrypto. It does not claim X25519 or
 * Ed25519 support. Native PQC and device identity integration belong behind a
 * separately verified adapter.
 *
 * Local/offline mode dispatches only a local DOM event. Hybrid/online transport
 * is injected by the caller and remains policy-gated; this module never invents
 * relay or satellite endpoints and never performs background listening.
 */
(function (global) {
  'use strict';

  var STATUS = {
    INIT: 'INIT',
    KEYGEN: 'KEYGEN',
    READY: 'READY',
    ERROR: 'ERROR'
  };

  function base64UrlEncode(buffer) {
    var bytes = new Uint8Array(buffer);
    var binary = '';
    for (var i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  function base64UrlDecode(value) {
    var normalized = String(value).replace(/-/g, '+').replace(/_/g, '/');
    while (normalized.length % 4) normalized += '=';
    var binary = atob(normalized);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function hex(buffer) {
    return Array.from(new Uint8Array(buffer)).map(function (value) {
      return value.toString(16).padStart(2, '0');
    }).join('');
  }

  function currentMode() {
    try { return localStorage.getItem('sgh_mode') || 'local'; } catch (error) { return 'local'; }
  }

  function isLocalMode(mode) {
    return mode === 'local' || mode === 'offline';
  }

  function create(options) {
    options = options || {};
    var cryptoApi = options.crypto || global.crypto;
    var eventTarget = options.eventTarget || global.document;
    var status = STATUS.INIT;
    var identity = null;
    var listeners = [];

    function setStatus(next, detail) {
      status = next;
      listeners.forEach(function (listener) {
        try { listener(next, detail); } catch (error) { /* observer isolation */ }
      });
    }

    function requireCrypto() {
      if (!cryptoApi || !cryptoApi.subtle) throw new Error('WebCrypto is unavailable');
    }

    async function init() {
      requireCrypto();
      if (identity) return identity;
      setStatus(STATUS.KEYGEN, 'Generating session identity');
      var dhKeyPair = await cryptoApi.subtle.generateKey(
        { name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']
      );
      var signKeyPair = await cryptoApi.subtle.generateKey(
        { name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']
      );
      var publicKey = await cryptoApi.subtle.exportKey('raw', signKeyPair.publicKey);
      identity = {
        dhKeyPair: dhKeyPair,
        signKeyPair: signKeyPair,
        fingerprint: hex(await cryptoApi.subtle.digest('SHA-256', publicKey)).slice(0, 16)
      };
      setStatus(STATUS.READY, identity.fingerprint);
      return identity;
    }

    async function deriveSession(remoteDhPublic) {
      var local = await init();
      var remote = await cryptoApi.subtle.importKey(
        'raw', remoteDhPublic,
        { name: 'ECDH', namedCurve: 'P-256' }, false, []
      );
      var shared = await cryptoApi.subtle.deriveBits(
        { name: 'ECDH', public: remote }, local.dhKeyPair.privateKey, 256
      );
      var material = await cryptoApi.subtle.importKey('raw', shared, 'HKDF', false, ['deriveKey']);
      return cryptoApi.subtle.deriveKey(
        {
          name: 'HKDF',
          hash: 'SHA-256',
          salt: new TextEncoder().encode('sovereign-hawking-v1'),
          info: new TextEncoder().encode('aes-gcm-session')
        },
        material,
        { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']
      );
    }

    async function seal(message, remoteDhPublic) {
      var local = await init();
      if (!remoteDhPublic) throw new Error('A recipient public key is required for sealing');
      var key = await deriveSession(remoteDhPublic);
      var iv = cryptoApi.getRandomValues(new Uint8Array(12));
      var plaintext = typeof message === 'string' ? message : JSON.stringify(message);
      var ciphertext = await cryptoApi.subtle.encrypt(
        { name: 'AES-GCM', iv: iv }, key, new TextEncoder().encode(plaintext)
      );
      var signature = await cryptoApi.subtle.sign(
        { name: 'ECDSA', hash: 'SHA-256' }, local.signKeyPair.privateKey, ciphertext
      );
      return {
        version: 1,
        algorithm: 'P-256-ECDH+A256GCM+ECDSA-SHA256',
        fingerprint: local.fingerprint,
        dhPublicKey: base64UrlEncode(await cryptoApi.subtle.exportKey('raw', local.dhKeyPair.publicKey)),
        iv: base64UrlEncode(iv),
        ciphertext: base64UrlEncode(ciphertext),
        signature: base64UrlEncode(signature),
        timestamp: Date.now()
      };
    }

    async function unseal(envelope, remoteDhPublic) {
      if (!envelope || envelope.version !== 1) throw new Error('Unsupported Hawking envelope');
      var key = await deriveSession(remoteDhPublic || base64UrlDecode(envelope.dhPublicKey));
      var plaintext = await cryptoApi.subtle.decrypt(
        { name: 'AES-GCM', iv: base64UrlDecode(envelope.iv) },
        key,
        base64UrlDecode(envelope.ciphertext)
      );
      return new TextDecoder().decode(plaintext);
    }

    async function send(message, optionsForSend) {
      optionsForSend = optionsForSend || {};
      var mode = optionsForSend.mode || currentMode();
      var envelope = await seal(message, optionsForSend.remoteDhPublic);

      if (isLocalMode(mode)) {
        if (eventTarget && typeof eventTarget.dispatchEvent === 'function') {
          eventTarget.dispatchEvent(new CustomEvent('sg:hawkingMsg', {
            detail: { envelope: envelope, local: true }
          }));
        }
        return { path: 'local', ok: true, envelope: envelope };
      }

      if (typeof optionsForSend.transport !== 'function') {
        return { path: 'unavailable', ok: false, envelope: envelope, reason: 'transport_not_configured' };
      }

      var result = await optionsForSend.transport(envelope, mode);
      return { path: 'configured-transport', ok: true, result: result, envelope: envelope };
    }

    return {
      init: init,
      seal: seal,
      unseal: unseal,
      send: send,
      getStatus: function () { return status; },
      getFingerprint: function () { return identity ? identity.fingerprint : null; },
      onStatus: function (listener) { listeners.push(listener); }
    };
  }

  global.SovereignHawkingChannel = { STATUS: STATUS, create: create };
}(typeof window !== 'undefined' ? window : globalThis));
