/* SGHv119 Runtime Hardening v1: mandatory trust boundary; bus remains dumb. */
(function (global) {
  'use strict';

  var MODES = Object.freeze({ LOCAL: 'LOCAL', GHOST: 'GHOST', HYBRID: 'HYBRID' });
  var NETWORK_ACTION = /^(net\.|cap\.)/;
  var REPLAY_WINDOW_MS = 60 * 1000;

  function canonical(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    return '{' + Object.keys(value).sort().map(function (key) {
      return JSON.stringify(key) + ':' + canonical(value[key]);
    }).join(',') + '}';
  }

  async function sha256(value) {
    if (!global.crypto || !global.crypto.subtle) throw new Error('WebCrypto is unavailable');
    var bytes = new TextEncoder().encode(typeof value === 'string' ? value : canonical(value));
    var digest = await global.crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest)).map(function (b) { return b.toString(16).padStart(2, '0'); }).join('');
  }

  function freezeMessage(message) {
    if (message.payload && typeof message.payload === 'object') Object.freeze(message.payload);
    return Object.freeze(message);
  }

  async function createMessage(command, options) {
    options = options || {};
    if (!command || typeof command !== 'object') throw new Error('command must be an object');
    var payload = command.payload === undefined ? {} : command.payload;
    var payloadHash = command.payload_hash || 'sha256:' + await sha256(payload);
    return freezeMessage({
      version: 1,
      message_id: options.messageId || command.message_id,
      created_at: options.createdAt || Date.now(),
      sender_id: command.sender_id,
      action: command.action,
      nonce: command.nonce,
      sequence: command.sequence,
      payload: payload,
      payload_hash: payloadHash,
      policy_hash: options.policyHash || command.policy_hash,
      runtime_version: options.runtimeVersion || 'sghv119-runtime-v1',
      mode: options.mode || command.mode
    });
  }

  function validateEnvelope(envelope) {
    if (!envelope || typeof envelope !== 'object') throw new Error('invalid_envelope');
    ['message_id', 'sender_id', 'action', 'nonce', 'ciphertext', 'envelope_hash', 'payload_hash', 'policy_hash', 'runtime_version'].forEach(function (field) {
      if (!envelope[field]) throw new Error(field + '_required');
    });
    if (envelope.version !== 1) throw new Error('unsupported_envelope_version');
    if (!Number.isInteger(envelope.sequence) || envelope.sequence < 1) throw new Error('sequence_required');
    if (!Number.isFinite(Number(envelope.timestamp))) throw new Error('timestamp_required');
    return true;
  }

  function createBus() {
    var subscribers = new Set();
    var closed = false;
    return {
      subscribe: function (handler) {
        if (closed) throw new Error('bus_closed');
        if (typeof handler !== 'function') throw new Error('subscriber_required');
        subscribers.add(handler);
        return function () { subscribers.delete(handler); };
      },
      publish: function (message) {
        if (closed) throw new Error('bus_closed');
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
    var replayWindowMs = options.replayWindowMs || REPLAY_WINDOW_MS;
    var eventTarget = options.eventTarget || null;
    var closed = false;
    var mode = null;
    var senders = new Map();
    var nonces = new Set();
    var sequences = new Map();

    if (!channel || typeof channel.verify !== 'function' || typeof channel.unseal !== 'function' || typeof channel.seal !== 'function') {
      throw new Error('hawking_channel_required');
    }

    function emit(type, envelope, reason, classification) {
      var event = {
        event_type: type,
        actor_type: 'machine',
        actor: 'SGHV119HawkingRuntime',
        subject: 'message',
        message_id: envelope && envelope.message_id,
        sender_id: envelope && envelope.sender_id,
        action: envelope && envelope.action,
        timestamp: new Date(now()).toISOString(),
        classification: classification || 'informational',
        mutation: false
      };
      if (reason) event.reason = reason;
      appendScar(event);
      return event;
    }

    function reject(envelope, reason, cause) {
      try { emit('HAWKING_MESSAGE_REJECTED', envelope || {}, reason, 'security'); } catch (_) {}
      var error = new Error(reason);
      if (cause) error.cause = cause;
      throw error;
    }

    function modeAllowed(envelope) {
      if (!mode || (envelope.mode && envelope.mode !== mode)) return false;
      if (mode === MODES.LOCAL && NETWORK_ACTION.test(String(envelope.action || ''))) return false;
      if ((mode === MODES.GHOST || mode === MODES.HYBRID) && !senders.has(envelope.sender_id)) return false;
      return true;
    }

    async function receive(envelope) {
      if (closed) return reject(envelope, 'runtime_closed');
      try { validateEnvelope(envelope); } catch (error) { return reject(envelope, 'invalid_envelope', error); }

      var age = now() - Number(envelope.timestamp);
      if (Math.abs(age) > replayWindowMs) return reject(envelope, 'replay_window_expired');
      if (nonces.has(envelope.nonce)) return reject(envelope, 'replay_detected');
      var previous = sequences.get(envelope.sender_id) || 0;
      if (envelope.sequence <= previous) return reject(envelope, 'sequence_regression');

      var verified;
      try { verified = await channel.verify(envelope); } catch (error) { return reject(envelope, 'cryptographic_validation_failed', error); }
      if (!verified) return reject(envelope, 'cryptographic_validation_failed');

      if (!senders.has(envelope.sender_id)) return reject(envelope, 'sender_identity_denied');
      if (!modeAllowed(envelope)) return reject(envelope, 'mode_policy_denied');

      var authorized;
      try { authorized = await authorize(envelope, { mode: mode, sender: senders.get(envelope.sender_id) }); } catch (error) { return reject(envelope, 'authorization_error', error); }
      if (!authorized) return reject(envelope, 'authorization_denied');

      // PRE_DELIVERY is the commit point. No bus publication is possible until this succeeds.
      try { emit('HAWKING_PRE_DELIVERY', envelope, 'authorized_for_delivery', 'pre_delivery'); }
      catch (error) { return reject(envelope, 'pre_delivery_scar_failed', error); }

      var plaintext;
      try { plaintext = await channel.unseal(envelope); } catch (error) { return reject(envelope, 'decrypt_failed', error); }
      var message;
      try { message = typeof plaintext === 'string' ? JSON.parse(plaintext) : plaintext; } catch (error) { return reject(envelope, 'deserialize_failed', error); }
      if (!message || typeof message !== 'object') return reject(envelope, 'deserialize_failed');
      if (message.payload_hash && message.payload_hash !== envelope.payload_hash) return reject(envelope, 'payload_hash_mismatch');

      nonces.add(envelope.nonce);
      sequences.set(envelope.sender_id, envelope.sequence);
      bus.publish(message);
      return message;
    }

    async function send(command, sendOptions) {
      if (closed) throw new Error('runtime_closed');
      sendOptions = sendOptions || {};
      var message = await createMessage(command, Object.assign({}, sendOptions, { mode: mode || sendOptions.mode }));
      if (!message.policy_hash) throw new Error('policy_hash_required');
      if (!senders.has(message.sender_id)) throw new Error('sender_identity_denied');
      if (mode === MODES.LOCAL && NETWORK_ACTION.test(String(message.action))) throw new Error('mode_policy_denied');
      if ((mode === MODES.GHOST || mode === MODES.HYBRID) && !senders.has(message.sender_id)) throw new Error('mode_policy_denied');
      return channel.seal(message, sendOptions.remoteDhPublic || sendOptions);
    }

    function onEvent(event) {
      if (!event || !event.detail || !event.detail.envelope) return;
      receive(event.detail.envelope).catch(function (error) {
        if (global.console && console.error) console.error('[SGHv119] receive failed', error);
      });
    }

    if (eventTarget && typeof eventTarget.addEventListener === 'function') eventTarget.addEventListener('sg:hawkingMsg', onEvent);

    return {
      send: send,
      receive: receive,
      setMode: function (nextMode) {
        if (!Object.prototype.hasOwnProperty.call(MODES, nextMode)) throw new Error('invalid_runtime_mode');
        if (closed) throw new Error('runtime_closed');
        mode = nextMode;
        emit('HAWKING_MODE_CHANGED', {}, nextMode, 'configuration');
        return mode;
      },
      getMode: function () { return mode; },
      registerSender: function (senderId, identity) {
        if (!senderId || !identity) throw new Error('sender_identity_required');
        senders.set(senderId, Object.freeze(Object.assign({}, identity)));
      },
      revokeSender: function (senderId) { senders.delete(senderId); },
      close: function () {
        if (closed) return;
        closed = true;
        if (eventTarget && typeof eventTarget.removeEventListener === 'function') eventTarget.removeEventListener('sg:hawkingMsg', onEvent);
        try { emit('HAWKING_CAPABILITY_REVOKED', {}, 'receive_capability_revoked', 'security'); } catch (_) {}
        try { emit('HAWKING_CLOSED', {}, 'runtime_closed', 'lifecycle'); } catch (_) {}
        senders.clear(); nonces.clear(); sequences.clear();
        if (bus && typeof bus.close === 'function') bus.close();
      },
      isClosed: function () { return closed; },
      options: function () { return options; }
    };
  }

  global.SGHV119Message = { create: createMessage };
  global.SGHV119Bus = { create: createBus };
  global.SGHV119HawkingRuntime = { create: create, validateEnvelope: validateEnvelope, MODES: MODES };
  if (typeof module !== 'undefined' && module.exports) module.exports = { SGHV119Message: global.SGHV119Message, SGHV119Bus: global.SGHV119Bus, SGHV119HawkingRuntime: global.SGHV119HawkingRuntime };
}(typeof window !== 'undefined' ? window : globalThis));
