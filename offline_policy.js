/* Offline-first transport gate. Load before application scripts. */
(function offlinePolicy(window) {
  'use strict';

  const loopback = new Set(['localhost', '127.0.0.1', '::1', '[::1]']);
  const state = {
    mode: 'offline',
    remoteEnabled: false,
    attempts: [],
  };

  function audit(action, detail) {
    const entry = { action, detail: String(detail || ''), timestamp: new Date().toISOString() };
    state.attempts.push(entry);
    if (state.attempts.length > 100) state.attempts.shift();
    window.dispatchEvent(new CustomEvent('sg:network-audit', { detail: entry }));
    if (typeof window.addAudit === 'function') window.addAudit(action, entry);
  }

  function permitted(value) {
    try {
      const url = new URL(value, window.location.href);
      return url.protocol === 'blob:' || url.protocol === 'data:' || loopback.has(url.hostname);
    } catch {
      return false;
    }
  }

  function block(value, kind) {
    audit('NETWORK_BLOCKED', `${kind}: ${value}`);
    throw new DOMException('Offline mode only permits loopback network access.', 'NetworkError');
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function guardedFetch(input, init) {
    const target = typeof input === 'string' ? input : input.url;
    if (!permitted(target)) return Promise.reject(block(target, 'fetch'));
    return nativeFetch(input, init);
  };

  const xhrOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function guardedOpen(method, url) {
    if (!permitted(url)) block(url, 'XMLHttpRequest');
    return xhrOpen.apply(this, arguments);
  };

  const NativeWebSocket = window.WebSocket;
  window.WebSocket = function GuardedWebSocket(url, protocols) {
    if (!permitted(url)) block(url, 'WebSocket');
    return protocols === undefined ? new NativeWebSocket(url) : new NativeWebSocket(url, protocols);
  };
  window.WebSocket.prototype = NativeWebSocket.prototype;

  window.SGOfflinePolicy = Object.freeze({
    status: () => Object.freeze({
      mode: state.mode,
      remoteEnabled: state.remoteEnabled,
      attempts: state.attempts.slice(),
    }),
    requestRemoteAccess: () => {
      audit('REMOTE_ACCESS_DENIED', 'This offline bundle cannot relax its local-only CSP.');
      return false;
    },
    isPermitted: permitted,
  });

  audit('OFFLINE_MODE_ENABLED', 'Local-only transport gate active');
}(window));
