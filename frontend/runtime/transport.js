/*
 * Single sovereign transport boundary.
 * Production transport is TLS-only: HTTPS for HTTP APIs and WSS for sockets.
 * Plain HTTP/WS is rejected rather than silently downgraded.
 */
(function (global) {
  'use strict';

  var DEFAULTS = {
    mode: 'offline',
    httpOrigin: 'https://127.0.0.1:9897',
    nodeOrigin: 'https://127.0.0.1:9899',
    wsOrigin: 'wss://127.0.0.1:9899'
  };

  function mode(value) {
    return value === 'local' || value === 'offline' || value === 'hybrid' || value === 'online'
      ? value
      : DEFAULTS.mode;
  }

  function config(overrides) {
    var input = overrides || {};
    var selected = mode(input.mode || DEFAULTS.mode);
    var result = {
      mode: selected,
      localOnly: selected === 'local' || selected === 'offline',
      httpOrigin: input.httpOrigin || DEFAULTS.httpOrigin,
      nodeOrigin: input.nodeOrigin || DEFAULTS.nodeOrigin,
      wsOrigin: input.wsOrigin || DEFAULTS.wsOrigin
    };
    assertSecureTransport(result.httpOrigin, 'HTTPS');
    assertSecureTransport(result.nodeOrigin, 'HTTPS');
    assertSecureTransport(result.wsOrigin, 'WSS');
    return result;
  }

  function isLoopback(url) {
    try {
      var parsed = new URL(url);
      return parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost' || parsed.hostname === '[::1]' || parsed.hostname === '::1';
    } catch (error) {
      return false;
    }
  }

  function assertSecureTransport(url, expected) {
    var parsed = new URL(url);
    var protocol = parsed.protocol.toLowerCase();
    var required = expected === 'WSS' ? 'wss:' : 'https:';
    if (protocol !== required) {
      throw new Error('Insecure transport rejected: expected ' + expected + ', got ' + protocol);
    }
    return true;
  }

  function assertAllowed(url, runtime) {
    var current = runtime || config();
    if (current.localOnly && !isLoopback(url)) {
      throw new Error('External network is disabled by local runtime policy.');
    }
    return true;
  }

  function endpoint(path, runtime) {
    var current = runtime || config();
    var suffix = String(path || '');
    if (suffix.charAt(0) !== '/') suffix = '/' + suffix;
    var url = current.httpOrigin + suffix;
    assertSecureTransport(url, 'HTTPS');
    assertAllowed(url, current);
    return url;
  }

  function nodeEndpoint(path, runtime) {
    var current = runtime || config();
    var suffix = String(path || '');
    if (suffix.charAt(0) !== '/') suffix = '/' + suffix;
    var url = current.nodeOrigin + suffix;
    assertSecureTransport(url, 'HTTPS');
    assertAllowed(url, current);
    return url;
  }

  function socketEndpoint(path, runtime) {
    var current = runtime || config();
    var suffix = String(path || '');
    if (suffix.charAt(0) !== '/') suffix = '/' + suffix;
    var url = current.wsOrigin + suffix;
    assertSecureTransport(url, 'WSS');
    assertAllowed(url.replace(/^wss:/, 'https:'), current);
    return url;
  }

  function health(runtime) {
    var current = runtime || config();
    return {
      mode: current.mode,
      network: current.localOnly ? 'loopback-only' : 'policy-gated',
      transport: 'HTTPS/WSS',
      status: 'not_checked'
    };
  }

  global.SovereignTransport = {
    defaults: DEFAULTS,
    config: config,
    isLoopback: isLoopback,
    assertSecureTransport: assertSecureTransport,
    assertAllowed: assertAllowed,
    endpoint: endpoint,
    nodeEndpoint: nodeEndpoint,
    socketEndpoint: socketEndpoint,
    health: health
  };
}(typeof window !== 'undefined' ? window : globalThis));
