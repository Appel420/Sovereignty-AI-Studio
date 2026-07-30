/*
 * Single local transport boundary for SGHV119 and related local UI surfaces.
 * External network access is never implied by a transport URL.
 */
(function (global) {
  'use strict';

  var DEFAULTS = {
    mode: 'offline',
    httpOrigin: 'http://127.0.0.1:9897',
    nodeOrigin: 'http://127.0.0.1:9899',
    wsOrigin: 'ws://127.0.0.1:9899'
  };

  function mode(value) {
    return value === 'local' || value === 'offline' || value === 'hybrid' || value === 'online'
      ? value
      : DEFAULTS.mode;
  }

  function config(overrides) {
    var input = overrides || {};
    var selected = mode(input.mode || DEFAULTS.mode);
    return {
      mode: selected,
      localOnly: selected === 'local' || selected === 'offline',
      httpOrigin: input.httpOrigin || DEFAULTS.httpOrigin,
      nodeOrigin: input.nodeOrigin || DEFAULTS.nodeOrigin,
      wsOrigin: input.wsOrigin || DEFAULTS.wsOrigin
    };
  }

  function isLoopback(url) {
    try {
      var parsed = new URL(url);
      return parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost' || parsed.hostname === '[::1]' || parsed.hostname === '::1';
    } catch (error) {
      return false;
    }
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
    assertAllowed(url, current);
    return url;
  }

  function nodeEndpoint(path, runtime) {
    var current = runtime || config();
    var suffix = String(path || '');
    if (suffix.charAt(0) !== '/') suffix = '/' + suffix;
    var url = current.nodeOrigin + suffix;
    assertAllowed(url, current);
    return url;
  }

  function socketEndpoint(path, runtime) {
    var current = runtime || config();
    var suffix = String(path || '');
    if (suffix.charAt(0) !== '/') suffix = '/' + suffix;
    var url = current.wsOrigin + suffix;
    assertAllowed(url.replace(/^ws(s?):/, 'http$1:'), current);
    return url;
  }

  function health(runtime) {
    var current = runtime || config();
    return {
      mode: current.mode,
      network: current.localOnly ? 'loopback-only' : 'policy-gated',
      transport: current.wsOrigin.indexOf('wss://') === 0 ? 'HTTPS/WSS' : 'HTTP/WS',
      status: 'not_checked'
    };
  }

  global.SovereignTransport = {
    defaults: DEFAULTS,
    config: config,
    isLoopback: isLoopback,
    assertAllowed: assertAllowed,
    endpoint: endpoint,
    nodeEndpoint: nodeEndpoint,
    socketEndpoint: socketEndpoint,
    health: health
  };
}(typeof window !== 'undefined' ? window : globalThis));
