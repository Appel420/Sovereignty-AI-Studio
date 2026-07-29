/*
 * SGHv119 Hawking integration boundary.
 *
 * This module owns one Hawking instance, one status surface, and one trusted
 * fingerprint decision. It is intentionally transport-neutral. The dashboard
 * must load hawking-channel.js before this file.
 */
(function (global) {
  'use strict';

  function normalizeFingerprint(value) {
    return String(value || '').trim().toLowerCase();
  }

  function create(options) {
    options = options || {};
    if (!global.SovereignHawkingChannel) {
      throw new Error('SovereignHawkingChannel must load before SGHv119 integration');
    }

    var channel = options.channel || global.SovereignHawkingChannel.create({
      crypto: options.crypto || global.crypto,
      eventTarget: options.eventTarget || global.document,
      CustomEvent: options.CustomEvent || global.CustomEvent
    });
    var trusted = new Set((options.trustedFingerprints || []).map(normalizeFingerprint).filter(Boolean));
    var statusElement = options.statusElement || null;
    var state = {
      channel: channel,
      trust: 'UNAVAILABLE',
      fingerprint: null,
      status: channel.getStatus()
    };

    function render() {
      if (!statusElement) return;
      statusElement.textContent = 'E2EE:' + state.status + ' · TRUST:' + state.trust;
      statusElement.dataset.hawkingStatus = state.status;
      statusElement.dataset.hawkingTrust = state.trust;
      statusElement.setAttribute('aria-label', 'Hawking ' + state.status + ', fingerprint trust ' + state.trust);
    }

    function setTrust(fingerprint) {
      var normalized = normalizeFingerprint(fingerprint);
      state.fingerprint = normalized || null;
      state.trust = normalized && trusted.has(normalized) ? 'VERIFIED' : 'UNTRUSTED';
      render();
      return state.trust;
    }

    function authorizeEnvelope(envelope) {
      if (!envelope || !envelope.fingerprint) return false;
      return setTrust(envelope.fingerprint) === 'VERIFIED';
    }

    channel.onStatus(function (status) {
      state.status = status;
      if (status === 'READY' && !state.fingerprint) state.fingerprint = channel.getFingerprint();
      render();
    });

    return {
      channel: channel,
      state: state,
      init: function () { return channel.init().then(function () { render(); return state; }); },
      setTrustedFingerprints: function (fingerprints) {
        trusted = new Set((fingerprints || []).map(normalizeFingerprint).filter(Boolean));
        return setTrust(state.fingerprint);
      },
      setTrust: setTrust,
      authorizeEnvelope: authorizeEnvelope,
      send: function (message, sendOptions) { return channel.send(message, sendOptions); },
      receive: async function (envelope, remoteDhPublic) {
        if (!authorizeEnvelope(envelope)) throw new Error('Hawking fingerprint is not trusted');
        return channel.unseal(envelope, remoteDhPublic);
      },
      getState: function () { return Object.assign({}, state); }
    };
  }

  global.SGHv119Hawking = { create: create, normalizeFingerprint: normalizeFingerprint };
}(typeof window !== 'undefined' ? window : globalThis));
