/*
 * SGHv119 canonical runtime bootstrap.
 *
 * Load after hawking-channel.js and sg-hawking-integration.js. This module
 * creates one Hawking integration instance and one status element if the page
 * has not already provided them. It does not start network polling, create
 * transport endpoints, or override the dashboard's visual layout.
 *
 * DevAssist420 is loaded as a separate, authority-blind adapter. It is not an
 * authorization source; consequential requests still return to the local Gate
 * and FoldAuthority boundary.
 */
(function (global) {
  'use strict';

  function ensureStatusElement() {
    var existing = global.document && global.document.getElementById('sgb-hawking');
    if (existing) return existing;
    if (!global.document || !global.document.body) return null;

    var status = global.document.createElement('span');
    status.id = 'sgb-hawking';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.textContent = 'E2EE:INIT · TRUST:UNAVAILABLE';
    status.style.cssText = [
      'display:inline-flex', 'align-items:center', 'min-height:44px',
      'padding:0 10px', 'color:#ffb300', 'font:700 8px monospace',
      'letter-spacing:.5px', 'white-space:nowrap'
    ].join(';');

    var bottomBar = global.document.getElementById('sg-bottom-bar');
    (bottomBar || global.document.body).appendChild(status);
    return status;
  }

  function loadTrustedFingerprints() {
    if (Array.isArray(global.SGH_TRUSTED_FINGERPRINTS)) {
      return global.SGH_TRUSTED_FINGERPRINTS;
    }
    return [];
  }

  function loadDevAssistAdapter() {
    if (global.SovereignDevAssist420) return Promise.resolve(global.SovereignDevAssist420);
    if (!global.document) return Promise.reject(new Error('document unavailable'));

    return new Promise(function (resolve, reject) {
      var existing = global.document.querySelector('script[data-sghv119-devassist420]');
      if (existing) {
        existing.addEventListener('load', function () { resolve(global.SovereignDevAssist420); }, { once: true });
        existing.addEventListener('error', function () { reject(new Error('DevAssist420 adapter failed to load')); }, { once: true });
        return;
      }

      var script = global.document.createElement('script');
      script.src = './frontend/runtime/devassist420-bridge.js';
      script.async = false;
      script.dataset.sghv119Devassist420 = 'true';
      script.onload = function () {
        if (!global.SovereignDevAssist420) {
          reject(new Error('DevAssist420 adapter loaded without API'));
          return;
        }
        resolve(global.SovereignDevAssist420);
      };
      script.onerror = function () {
        reject(new Error('DevAssist420 adapter failed to load'));
      };
      (global.document.head || global.document.documentElement).appendChild(script);
    });
  }

  function boot() {
    if (global.SGHv119HawkingRuntime) return global.SGHv119HawkingRuntime;
    if (!global.SGHv119Hawking) {
      throw new Error('SGHv119 Hawking integration module is not loaded');
    }

    var runtime = global.SGHv119Hawking.create({
      statusElement: ensureStatusElement(),
      trustedFingerprints: loadTrustedFingerprints()
    });
    global.SGHv119HawkingRuntime = runtime;
    runtime.init().catch(function (error) {
      if (global.console && console.warn) {
        console.warn('[SGHv119] Hawking unavailable:', error.message);
      }
    });

    loadDevAssistAdapter().then(function () {
      if (global.console && console.info) {
        console.info('[SGHv119] DevAssist420 boundary loaded');
      }
    }).catch(function (error) {
      if (global.console && console.warn) {
        console.warn('[SGHv119] DevAssist420 unavailable:', error.message);
      }
    });

    return runtime;
  }

  global.SGHv119Runtime = {
    bootHawking: boot,
    loadDevAssist420: loadDevAssistAdapter
  };

  if (global.document) {
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
      boot();
    }
  }
}(typeof window !== 'undefined' ? window : globalThis));
