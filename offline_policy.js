/* Three-mode transport gate. Load before application scripts. */
(function networkPolicy(window) {
  'use strict';

  const loopback = new Set(['localhost', '127.0.0.1', '::1', '[::1]']);
  const state = { attempts: [] };

  function mode() {
    const saved = sessionStorage.getItem('sg_mode') || localStorage.getItem('sgh_mode');
    return (window.ST && window.ST.mode) || saved || 'offline';
  }

  function audit(action, detail) {
    const entry = { action, detail: String(detail || ''), mode: mode(), timestamp: new Date().toISOString() };
    state.attempts.push(entry);
    if (state.attempts.length > 100) state.attempts.shift();
    window.dispatchEvent(new CustomEvent('sg:network-audit', { detail: entry }));
    if (typeof window.addAudit === 'function') window.addAudit(action, entry);
  }

  function hybridOrigins() {
    try { return new Set(JSON.parse(sessionStorage.getItem('sg_hybrid_origins') || '[]')); }
    catch { return new Set(); }
  }

  function permitted(value) {
    try {
      const url = new URL(value, window.location.href);
      if (url.protocol === 'blob:' || url.protocol === 'data:') return true;
      if (loopback.has(url.hostname)) return true;
      if (mode() === 'hybrid') return hybridOrigins().has(url.origin);
      return mode() === 'online' && sessionStorage.getItem('sg_online_opt_in') === '1';
    } catch {
      return false;
    }
  }

  function block(value, kind) {
    audit('NETWORK_BLOCKED', `${kind}: ${value}`);
    throw new DOMException(`${mode()} mode denied this network request.`, 'NetworkError');
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function guardedFetch(input, init) {
    const target = typeof input === 'string' ? input : input.url;
    if (!permitted(target)) {
      audit('NETWORK_BLOCKED', `fetch: ${target}`);
      return Promise.reject(new DOMException(`${mode()} mode denied this network request.`, 'NetworkError'));
    }
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
  window.WebSocket.CONNECTING = NativeWebSocket.CONNECTING;
  window.WebSocket.OPEN       = NativeWebSocket.OPEN;
  window.WebSocket.CLOSING    = NativeWebSocket.CLOSING;
  window.WebSocket.CLOSED     = NativeWebSocket.CLOSED;

  window.sgExternalApisAllowed = () => mode() === 'online' && sessionStorage.getItem('sg_online_opt_in') === '1';
  window.SGOfflinePolicy = Object.freeze({
    status: () => Object.freeze({ mode: mode(), onlineOptIn: window.sgExternalApisAllowed(), attempts: state.attempts.slice() }),
    approveHybridEndpoint: (value) => {
      const url = new URL(value, window.location.href);
      if (loopback.has(url.hostname)) return true;
      const origins = hybridOrigins();
      origins.add(url.origin);
      sessionStorage.setItem('sg_hybrid_origins', JSON.stringify([...origins]));
      audit('HYBRID_ENDPOINT_APPROVED', url.origin);
      return true;
    },
    enableOnline: () => {
      if (!window.confirm('Enable fully online mode for this browser session?')) return false;
      sessionStorage.setItem('sg_online_opt_in', '1');
      audit('ONLINE_MODE_APPROVED', 'User granted session-only remote access');
      return true;
    },
    disableOnline: () => {
      sessionStorage.removeItem('sg_online_opt_in');
      audit('ONLINE_MODE_REVOKED', 'Remote access disabled');
    },
    isPermitted: permitted,
  });

  audit('NETWORK_MODE_READY', 'Offline, hybrid, and online policy gate active');
}(window));
