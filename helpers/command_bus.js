/* SGHV119 command bus: one routing spine for UI, voice, terminal, bridge, agents, council, fixers, and bug hunters. */
(function () {
  'use strict';

  const handlers = new Map();
  const history = [];

  function now() {
    return new Date().toISOString();
  }

  function id() {
    if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'cmd-' + Date.now() + '-' + Math.random().toString(16).slice(2);
  }

  function normalize(command) {
    if (!command || typeof command !== 'object') throw new Error('Command must be an object');
    if (!command.type) throw new Error('Command type is required');
    return {
      id: command.id || id(),
      type: String(command.type),
      source: command.source || 'sghv119',
      target: command.target || 'system',
      payload: command.payload || {},
      meta: command.meta || {},
      createdAt: command.createdAt || now()
    };
  }

  function subscribe(type, handler) {
    if (!handlers.has(type)) handlers.set(type, new Set());
    handlers.get(type).add(handler);
    return () => handlers.get(type).delete(handler);
  }

  async function publish(command) {
    const normalized = normalize(command);
    history.push(normalized);
    if (history.length > 200) history.shift();

    const direct = handlers.get(normalized.type) || new Set();
    const wildcard = handlers.get('*') || new Set();
    const targets = [...direct, ...wildcard];

    const results = [];
    for (const handler of targets) {
      results.push(await handler(normalized));
    }
    return { command: normalized, results };
  }

  globalThis.SGHV119Bus = { publish, subscribe, history: () => history.slice() };
})();
