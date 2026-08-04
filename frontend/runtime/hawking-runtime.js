/*
 * SGHv119 governed Hawking runtime.
 *
 * The channel performs cryptographic transport. This module owns the trust
 * boundary: envelope validation, authorization, replay protection, SCAR-before-
 * publish ordering, and lifecycle revocation. It is intentionally dependency
 * injected so local tests can exercise every boundary without network access.
 */
(function (global) {
  'use strict';

  var ZERO_HASH = '0'.repeat(64);
  var DEFAULT_REPLAY_WINDOW_MS = 60 * 1000;

  function canonical(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    return '{' + Object.keys(value).sort().map(function (key) {
      return JSON.stringify(key) + ':' + canonical(value[key]);
    }).join(',') + '}';
  }

  function freezeMessage(message) {
    Object.freeze(message);
    if (message.payload && typeof message.payload === 'object') Object.freeze(message.payload);
    return message;
  }

  function createMessage(command, options) {
    options = options || {};
    if (!command || typeof command !== 'object') throw new Error('command must be an object');
    var message = {
      version: 1,
      message_id: options.messageId || command.message_id,
      created_at: options.createdAt || Date.now(),
      sender_id: command.sender_id,
      action: command.action,
      nonce: command.nonce,
      sequence: command.sequence,
      payload: command.payload,
      payload_hash: command.payload_hash || 'sha256:' + canonical(command.payload || {}),
      policy_hash: options.policyHash || command.policy_hash || 'sha256:unbound',
      runtime_version: options.runtimeVersion || 'sghv119-runtime-1'
    };
    if (!message.message_id) throw new Error('message_id is required');
    if (!message.sender_id) throw new Error('sender_id is required');
    if (!message.action) throw new Error('action is required');
    if (!message.nonce) throw new Error('nonce is required');
    if (!Number.isInteger(message.sequence) || message.sequence < 1) throw new Error('sequence is required');
    return freezeMessage(message);
  }

  function validateEnvelope(envelope) {
    if (!envelope || typeof envelope !== 'object') throw new Error('invalid envelope');
    if (envelope.version !== 1) throw new Error('unsupported envelope version');
    if (!envelope.message_id) throw new Error('message_id is required');
    if (!envelope.sender_id) throw new Error('sender identity is required');
    if (!envelope.action) throw new Error('action is required');
    if (!envelope.nonce) throw new Error('nonce is required');
    if (!Number.isInteger(envelope.sequence) || envelope.sequence < 1) throw new Error('sequence is required');
    if (!envelope.ciphertext) throw new Error('ciphertext is required');
    return true;
  }

  function createBus() {
    var subscribers = new Set();
    var closed = false;
    return {
      subscribe: function (handler) {
        if (closed) throw new Error('bus is closed');
        subscribers.add(handler);
        return function () { subscribers.delete(handler); };
      },
      publish: function (message) {
        if (closed) throw new Error('bus is closed');
        subscribers.forEach(function (handler) { handler(message); });
      },
      close: function () { closed = true; subscribers.clear(); },
      isClosed: function () { return closed; }
    };
  }

  function create(options) {
    options = options || {};
    var channel = options.channel;
    var bus = options.bus || createBus();
    var authorize = options.authorize || function () { return true; };
    var appendScar = options.appendScar || function () {};
    var now = options.now || function () { return Date.now(); };
    var replayWindowMs = options.replayWindowMs || DEFAULT_REPLAY_WINDOW_MS;
    var eventTarget = options.eventTarget || null;
    var closed = false;
    var seenNonces = new Set();
    var highestSequence = new Map();

    if (!channel || typeof channel.verify !== 'function' || typeof channel.unseal !== 'function') {
      throw new Error('Hawking channel with verify and unseal is required');
    }

    function scar(eventType, envelope, reason, classification) {
      var event = {
        event_type: eventType,
        actor: 'sghv119_hawking_runtime',
        subject: 'message',
        message_id: envelope && envelope.message_id,
        sender_id: envelope && envelope.sender_id,
        action: envelope && envelope.action,
        classification: classification || 'informational',
        mutation: false,
        timestamp: new Date(now()).toISOString()
      };
      if (reason) event.reason = reason;
      appendScar(event);
      return event;
    }

    function reject(envelope, reason, error) {
      scar('HAWKING_MESSAGE_REJECTED', envelope || {}, reason, 'review_required');
      var failure = new Error(reason);
      if (error) failure.cause = error;
      throw failure;
    }

    async function receive(envelope) {
      if (closed) return reject(envelope, 'runtime_closed');
      try { validateEnvelope(envelope); } catch (error) { return reject(envelope, 'invalid_envelope', error); }

      var age = now() - Number(envelope.timestamp || now());
      if (age > replayWindowMs || age < -replayWindowMs) return reject(envelope, 'message_expired');
      if (seenNonces.has(envelope.nonce)) return reject(envelope, 'replay_detected');
      var previous = highestSequence.get(envelope.sender_id) || 0;
      if (envelope.sequence <= previous) return reject(envelope, 'sequence_regression');

      var valid;
      try { valid = await channel.verify(envelope); } catch (error) { return reject(envelope, 'invalid_signature', error); }
      if (!valid) return reject(envelope, 'invalid_signature');

      var authorized;
      try { authorized = await authorize(envelope); } catch (error) { return reject(envelope, 'authorization_error', error); }
      if (!authorized) return reject(envelope, 'authorization_denied');

      seenNonces.add(envelope.nonce);
      highestSequence.set(envelope.sender_id, envelope.sequence);
      scar('HAWKING_MESSAGE_ACCEPTED', envelope);

      var plaintext;
      try { plaintext = await channel.unseal(envelope); } catch (error) { return reject(envelope, 'decrypt_failed', error); }
      var message;
      try { message = typeof plaintext === 'string' ? JSON.parse(plaintext) : plaintext; } catch (error) { return reject(envelope, 'invalid_plaintext', error); }
      if (!message || typeof message !== 'object') return reject(envelope, 'invalid_plaintext');
      bus.publish(message);
      return message;
    }

    async function send(command, sendOptions) {
      if (closed) throw new Error('runtime is closed');
      var message = createMessage(command, sendOptions);
      var envelope = await channel.seal(message, sendOptions || {});
      return envelope;
    }

    function onEvent(event) {
      if (!event || !event.detail || !event.detail.envelope) return;
      receive(event.detail.envelope).catch(function (error) {
        if (global.console && console.error) console.error('[SGHv119] receive failed', error);
      });
    }

    if (eventTarget && typeof eventTarget.addEventListener === 'function') {
      eventTarget.addEventListener('sg:hawkingMsg', onEvent);
    }

    return {
      send: send,
      receive: receive,
      close: function () {
        if (closed) return;
        closed = true;
        if (eventTarget && typeof eventTarget.removeEventListener === 'function') eventTarget.removeEventListener('sg:hawkingMsg', onEvent);
        scar('HAWKING_RUNTIME_CLOSED', {}, 'runtime_closed');
        if (bus && typeof bus.close === 'function') bus.close();
      },
      isClosed: function () { return closed; },
      options: function () { return options; }
    };
  }

  global.SGHV119Message = { create: createMessage };
  global.SGHV119Bus = { create: createBus };
  global.SGHV119HawkingRuntime = { create: create, validateEnvelope: validateEnvelope };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SGHV119Message: global.SGHV119Message, SGHV119Bus: global.SGHV119Bus, SGHV119HawkingRuntime: global.SGHV119HawkingRuntime };
  }
}(typeof window !== 'undefined' ? window : globalThis));
