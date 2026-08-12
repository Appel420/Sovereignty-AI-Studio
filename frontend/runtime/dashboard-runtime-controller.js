/*
 * Canonical SGHv119 dashboard runtime controller.
 *
 * One state owner for the top/bottom mode controls. Mode selection is not
 * authorization and does not prove transport connectivity. External routing
 * remains governed by offline_policy.js and an explicit caller transport.
 */
(function (global) {
  'use strict';

  var MODES = Object.freeze(['local', 'offline', 'hybrid', 'online']);
  var STORAGE_KEY = 'sgh_mode';

  function normalizeMode(value) {
    return MODES.indexOf(value) >= 0 ? value : 'local';
  }

  function readMode() {
    try {
      return normalizeMode(global.sessionStorage.getItem('sg_mode') ||
        global.localStorage.getItem(STORAGE_KEY) || 'local');
    } catch (error) {
      return 'local';
    }
  }

  function writeMode(mode) {
    try {
      global.localStorage.setItem(STORAGE_KEY, mode);
      global.sessionStorage.setItem('sg_mode', mode);
    } catch (error) {
      // Storage is optional; the in-memory state remains authoritative for this page.
    }
  }

  function localMode(mode) {
    return mode === 'local' || mode === 'offline';
  }

  function create(options) {
    options = options || {};
    var eventTarget = options.eventTarget || global.document;
    var controls = options.controls || [];
    var statusElements = options.statusElements || [];
    var state = {
      mode: readMode(),
      network: 'not_checked',
      transport: 'not_checked',
      deviceState: 'DEVICE_LOCAL',
      externalMemory: 'DISABLED',
      authorization: 'NOT_EVALUATED',
      approvalRequired: false,
      selected: true
    };

    function emit() {
      if (!eventTarget || typeof eventTarget.dispatchEvent !== 'function') return;
      var EventCtor = options.CustomEvent || global.CustomEvent;
      if (typeof EventCtor !== 'function') return;
      eventTarget.dispatchEvent(new EventCtor('sg:modeChanged', { detail: getState() }));
      eventTarget.dispatchEvent(new EventCtor('sg:runtimeStateChanged', { detail: getState() }));
    }

    function render() {
      controls.forEach(function (control) {
        if (!control) return;
        var value = control.getAttribute('data-sg-mode') || control.value;
        var active = normalizeMode(value) === state.mode;
        control.classList.toggle('active', active);
        control.setAttribute('aria-pressed', active ? 'true' : 'false');
        control.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      statusElements.forEach(function (element) {
        if (!element) return;
        element.textContent = 'MODE: ' + state.mode.toUpperCase() +
          ' · NETWORK: ' + state.network.toUpperCase() +
          ' · STATE: ' + state.deviceState;
        element.dataset.runtimeMode = state.mode;
        element.dataset.networkStatus = state.network;
        element.dataset.authorization = state.authorization;
      });
    }

    function setMode(nextMode) {
      var mode = normalizeMode(nextMode);
      state.mode = mode;
      state.network = localMode(mode) ? 'loopback_only' : 'policy_gated';
      state.transport = 'not_checked';
      state.deviceState = 'DEVICE_LOCAL';
      state.externalMemory = 'DISABLED';
      state.approvalRequired = mode === 'hybrid' || mode === 'online';
      state.authorization = state.approvalRequired ? 'REQUIRE_APPROVAL' : 'NOT_REQUIRED';
      writeMode(mode);
      render();
      emit();
      return getState();
    }

    function refresh() {
      render();
      emit();
      return getState();
    }

    function setTransportStatus(network, transport) {
      state.network = String(network || 'not_checked');
      state.transport = String(transport || 'not_checked');
      render();
      emit();
      return getState();
    }

    function getState() {
      return Object.assign({}, state);
    }

    controls.forEach(function (control) {
      if (!control || typeof control.addEventListener !== 'function') return;
      control.addEventListener('click', function () {
        setMode(control.getAttribute('data-sg-mode') || control.value);
      });
      control.addEventListener('change', function () {
        setMode(control.getAttribute('data-sg-mode') || control.value);
      });
    });

    setMode(state.mode);

    return {
      getState: getState,
      setMode: setMode,
      refresh: refresh,
      setTransportStatus: setTransportStatus,
      modes: MODES.slice()
    };
  }

  global.SGHv119RuntimeController = Object.freeze({
    MODES: MODES,
    create: create,
    normalizeMode: normalizeMode
  });
}(typeof window !== 'undefined' ? window : globalThis));
