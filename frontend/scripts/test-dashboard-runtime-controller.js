'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'runtime', 'dashboard-runtime-controller.js'),
  'utf8',
);

function makeContext() {
  const listeners = {};
  const storage = new Map();
  const document = {
    dispatchEvent(event) {
      (listeners[event.type] || []).forEach((listener) => listener(event));
    },
  };
  const context = {
    globalThis: {},
    document,
    CustomEvent: function CustomEvent(type, init) {
      this.type = type;
      this.detail = init && init.detail;
    },
    localStorage: {
      getItem: (key) => storage.get(`local:${key}`) || null,
      setItem: (key, value) => storage.set(`local:${key}`, String(value)),
    },
    sessionStorage: {
      getItem: (key) => storage.get(`session:${key}`) || null,
      setItem: (key, value) => storage.set(`session:${key}`, String(value)),
    },
    console,
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  return { context, document, listeners, storage };
}

function control(mode) {
  const attrs = { 'data-sg-mode': mode };
  return {
    classList: { toggle(name, value) { this[name] = value; } },
    dataset: {},
    getAttribute(name) { return attrs[name] || null; },
    setAttribute(name, value) { attrs[name] = value; },
    addEventListener(name, handler) { this[`on${name}`] = handler; },
  };
}

test('top and bottom controls share one mode state', () => {
  const { context, document } = makeContext();
  const top = control('online');
  const bottom = control('online');
  const events = [];
  document.addEventListener = (type, listener) => {
    (events[type] ||= []).push(listener);
  };

  const runtime = context.globalThis.SGHv119RuntimeController.create({
    eventTarget: document,
    controls: [top, bottom],
    statusElements: [],
  });

  runtime.setMode('online');
  assert.equal(runtime.getState().mode, 'online');
  assert.equal(runtime.getState().authorization, 'REQUIRE_APPROVAL');
  assert.equal(top.classList.active, true);
  assert.equal(bottom.classList.active, true);
  assert.ok(events['sg:modeChanged'].length >= 1);
});

test('local mode remains device-local and does not imply connectivity', () => {
  const { context } = makeContext();
  const runtime = context.globalThis.SGHv119RuntimeController.create();
  const state = runtime.setMode('local');
  assert.equal(state.network, 'loopback_only');
  assert.equal(state.transport, 'not_checked');
  assert.equal(state.deviceState, 'DEVICE_LOCAL');
  assert.equal(state.externalMemory, 'DISABLED');
  assert.equal(state.authorization, 'NOT_REQUIRED');
});

test('invalid mode falls back to local', () => {
  const { context } = makeContext();
  const runtime = context.globalThis.SGHv119RuntimeController.create();
  assert.equal(runtime.setMode('invalid').mode, 'local');
});
