/* SGHV119 command bus: one routing spine for UI, voice, terminal, bridge, agents, council, fixers, and bug hunters. */
(function () {
  'use strict';

  const handlers = new Map();
  const history = [];
  const branchOwners = Object.freeze({
    'ara-hardened': ['security', 'attestation', 'hardening'],
    'claude': ['implementation', 'refactor'],
    'gpt': ['architecture', 'integration', 'verification'],
    'copilot': ['code-assistance', 'fixes'],
    'devassist420': ['routing', 'coordination'],
    'sovereignty-ai': ['policy', 'governance', 'evidence'],
    'family': ['family', 'usability', 'sanitization'],
    'owner': ['architecture', 'approval', 'ownership']
  });

  function now() { return new Date().toISOString(); }
  function id() {
    if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'cmd-' + Date.now() + '-' + Math.random().toString(16).slice(2);
  }

  function routeAgentCommand(command) {
    const branch = command.branch || command.meta?.branch || command.target;
    if (!branch || !Object.prototype.hasOwnProperty.call(branchOwners, branch)) {
      return { status: 'unassigned', branch: null, reason: 'not an agent command' };
    }
    if (branch === 'main') throw new Error('Direct agent writes to main are forbidden');
    const scope = Array.isArray(command.scope)
      ? command.scope.map(String)
      : Array.isArray(command.meta?.scope) ? command.meta.scope.map(String) : [];
    const allowed = branchOwners[branch];
    const invalid = scope.filter(item => !allowed.includes(item));
    if (invalid.length) {
      throw new Error(`Branch ${branch} does not own scope: ${invalid.join(', ')}`);
    }
    return { status: 'assigned', branch, scope, writePolicy: 'branch-only' };
  }

  function normalize(command) {
    if (!command || typeof command !== 'object') throw new Error('Command must be an object');
    if (!command.type) throw new Error('Command type is required');
    const normalized = {
      id: command.id || id(),
      type: String(command.type),
      source: command.source || 'sghv119',
      target: command.target || 'system',
      payload: command.payload || {},
      meta: command.meta || {},
      createdAt: command.createdAt || now()
    };
    if (normalized.type.startsWith('agent.')) normalized.route = routeAgentCommand(command);
    return normalized;
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
    const results = [];
    for (const handler of [...direct, ...wildcard]) results.push(await handler(normalized));
    return { command: normalized, results };
  }

  globalThis.SGHV119Bus = {
    publish,
    subscribe,
    history: () => history.slice(),
    routeAgentCommand
  };
})();
