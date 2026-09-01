/*
 * Sovereign DevAssist420 ↔ SGHv119 boundary.
 *
 * Presentation code must call this adapter instead of calling an agent/model
 * endpoint directly. This module is deliberately authority-blind: it can
 * request a capability, but it cannot grant one. The local DevAssist service
 * is expected to perform authentication, policy/risk disclosure, owner
 * confirmation, FoldAuthority grant/regrant, and authorize-and-commit before
 * executing consequential work.
 */
(function (root) {
  'use strict';

  const ALLOWED_STATES = new Set([
    'DECLARED', 'CONFIGURED', 'AVAILABLE', 'VERIFIED', 'ACTIVE',
    'UNAVAILABLE', 'DENY', 'REQUIRE_APPROVAL'
  ]);

  function requireNonEmpty(value, field) {
    if (typeof value !== 'string' || value.trim() === '') {
      throw new Error(field + ' is required');
    }
    return value.trim();
  }

  function normalizeResource(input) {
    const resource = input || {};
    return Object.freeze({
      kind: requireNonEmpty(resource.kind, 'resource.kind'),
      id: requireNonEmpty(resource.id, 'resource.id'),
      provider: resource.provider ? String(resource.provider).trim() : 'local',
      operation: requireNonEmpty(resource.operation, 'resource.operation'),
    });
  }

  function normalizeRequest(input) {
    const request = input || {};
    const resource = normalizeResource(request.resource);
    const risks = Array.isArray(request.risk_notes) ? request.risk_notes.map(String) : [];
    const rewards = Array.isArray(request.reward_notes) ? request.reward_notes.map(String) : [];
    return Object.freeze({
      request_id: request.request_id || (root.crypto && root.crypto.randomUUID
        ? root.crypto.randomUUID() : 'devassist-' + Date.now()),
      resource,
      purpose: requireNonEmpty(request.purpose, 'purpose'),
      risk_notes: Object.freeze(risks),
      reward_notes: Object.freeze(rewards),
      owner_authenticated: request.owner_authenticated === true,
      session_id: request.session_id ? String(request.session_id) : null,
    });
  }

  async function requestCapability(input, options) {
    const request = normalizeRequest(input);
    const opts = options || {};
    if (!request.owner_authenticated) {
      return { state: 'REQUIRE_APPROVAL', reason: 'OWNER_AUTHENTICATION_REQUIRED', request };
    }

    const endpoint = opts.endpoint || '/api/devassist420/authorize';
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Sovereignty-Protocol': 'devassist420-v1' },
      body: JSON.stringify(request),
      credentials: 'same-origin',
    });

    if (!response.ok) {
      return { state: 'DENY', reason: 'AUTHORIZATION_SERVICE_UNAVAILABLE', request };
    }

    const result = await response.json();
    if (!result || !ALLOWED_STATES.has(result.state)) {
      return { state: 'DENY', reason: 'INVALID_AUTHORIZATION_RESULT', request };
    }
    return result;
  }

  async function executeAuthorized(authorization, input, options) {
    if (!authorization || authorization.state !== 'AUTHORIZED') {
      throw new Error('Execution requires an AUTHORIZED result');
    }
    if (!authorization.capability_id || !authorization.epoch || !authorization.session_id) {
      throw new Error('Authorized result is missing bound capability/session/epoch');
    }

    const opts = options || {};
    const endpoint = opts.endpoint || '/api/devassist420/execute';
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Sovereignty-Protocol': 'devassist420-v1' },
      credentials: 'same-origin',
      body: JSON.stringify({
        request: normalizeRequest(input),
        capability_id: authorization.capability_id,
        session_id: authorization.session_id,
        epoch: authorization.epoch,
      }),
    });

    if (!response.ok) throw new Error('DevAssist execution boundary rejected request');
    return response.json();
  }

  root.SovereignDevAssist420 = Object.freeze({
    requestCapability,
    executeAuthorized,
    normalizeRequest,
  });
})(window);
