/*
 * SGHv119 <-> Sovereign-DevAssist420 integration boundary.
 *
 * This browser module is a presentation/session adapter only. It does NOT
 * authorize work, hold owner secrets, grant capabilities, or execute tools.
 * The authoritative decision remains on the device-local Gate/Fold service.
 *
 * Transport is same-origin by default so a production Studio served over
 * HTTPS/WSS on 443 does not silently downgrade to an external endpoint.
 */
(function (global) {
  'use strict';

  var STATES = Object.freeze({
    SIGNED_OUT: 'SIGNED_OUT',
    AUTHENTICATED: 'AUTHENTICATED',
    SESSION_ACTIVE: 'SESSION_ACTIVE',
    CLOSING: 'CLOSING',
    CLOSED: 'CLOSED'
  });

  var DECISIONS = Object.freeze({
    AUTHORIZED: 'AUTHORIZED',
    ACCESS_DENIED: 'ACCESS_DENIED',
    NOT_ADMISSIBLE: 'NOT_ADMISSIBLE'
  });

  function Integration(options) {
    options = options || {};
    this.endpoint = options.endpoint || '/api/devassist';
    this.statusElement = options.statusElement || null;
    this.state = STATES.SIGNED_OUT;
    this.sessionId = null;
    this.transientState = Object.create(null);
    this.ownerState = null;
    this._closed = false;
  }

  Integration.prototype._setStatus = function (text) {
    if (this.statusElement) this.statusElement.textContent = text;
  };

  Integration.prototype._assertSecureTransport = function () {
    if (global.location && global.location.protocol === 'https:') return;
    if (global.isSecureContext) return;
    throw new Error('DEVASSIST_TRANSPORT_NOT_SECURE');
  };

  Integration.prototype._request = async function (path, payload, options) {
    this._assertSecureTransport();
    options = options || {};
    var headers = { 'Content-Type': 'application/json' };
    var ownerSession = global.SGHV119_OWNER_SESSION;
    if (typeof ownerSession === 'string' && ownerSession.length > 0) {
      headers['X-SGHV119-Owner-Session'] = ownerSession;
    }
    var response = await global.fetch(this.endpoint + path, {
      method: options.method || 'POST',
      headers: headers,
      credentials: 'same-origin',
      cache: 'no-store',
      body: JSON.stringify(payload || {})
    });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      var error = new Error(data.reason || data.error || 'DEVASSIST_REQUEST_FAILED');
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  };

  Integration.prototype.status = async function () {
    this._assertSecureTransport();
    var response = await global.fetch(this.endpoint + '/status', {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) throw new Error(data.reason || 'DEVASSIST_STATUS_FAILED');
    this._setStatus('DevAssist: ' + (data.status || 'UNKNOWN'));
    return data;
  };

  Integration.prototype.beginSession = async function (ownerContext) {
    if (this.state !== STATES.AUTHENTICATED && this.state !== STATES.SIGNED_OUT) {
      throw new Error('DEVASSIST_SESSION_ALREADY_ACTIVE');
    }
    var result = await this._request('/session/open', {
      owner_authenticated: true,
      owner_context: ownerContext || null
    });
    if (!result.session_id) throw new Error('DEVASSIST_SESSION_ID_MISSING');
    this.sessionId = result.session_id;
    this.state = STATES.SESSION_ACTIVE;
    this.transientState = Object.create(null);
    this._closed = false;
    this._setStatus('DevAssist: SESSION_ACTIVE');
    return result;
  };

  Integration.prototype.propose = async function (request) {
    if (this.state !== STATES.SESSION_ACTIVE || !this.sessionId) {
      throw new Error('DEVASSIST_SESSION_NOT_ACTIVE');
    }
    if (!request || typeof request !== 'object') throw new Error('DEVASSIST_REQUEST_INVALID');
    if (!request.resource || !request.operation || !request.purpose) {
      throw new Error('DEVASSIST_REQUEST_INCOMPLETE');
    }
    var result = await this._request('/proposal', {
      session_id: this.sessionId,
      request: request,
      authority: 'NONE',
      execution: 'NOT_REQUESTED'
    });
    this.transientState.lastProposal = result;
    return result;
  };

  Integration.prototype.executeApproved = async function (approvalReceipt) {
    if (this.state !== STATES.SESSION_ACTIVE || !this.sessionId) {
      throw new Error('DEVASSIST_SESSION_NOT_ACTIVE');
    }
    if (!approvalReceipt || approvalReceipt.decision !== DECISIONS.AUTHORIZED) {
      throw new Error('DEVASSIST_EXECUTION_REQUIRES_AUTHORIZED_RECEIPT');
    }
    return this._request('/execute', {
      session_id: this.sessionId,
      authorization_receipt: approvalReceipt
    });
  };

  Integration.prototype.closeSession = async function () {
    if (this.state === STATES.CLOSED || this.state === STATES.SIGNED_OUT) return;
    this.state = STATES.CLOSING;
    var sessionId = this.sessionId;
    try {
      if (sessionId) {
        await this._request('/session/close', {
          session_id: sessionId,
          persist_owner_state: false,
          destroy_transient_state: true,
          revoke_capabilities: true
        });
      }
    } finally {
      this.sessionId = null;
      this.transientState = Object.create(null);
      this.ownerState = null;
      this.state = STATES.CLOSED;
      this._closed = true;
      this._setStatus('DevAssist: CLOSED · NO AUTHORITY');
    }
  };

  Integration.prototype.handleVoiceCommand = async function (detail) {
    if (!detail || typeof detail.text !== 'string' || !detail.text.trim()) {
      throw new Error('DEVASSIST_VOICE_INPUT_INVALID');
    }
    return this.propose({
      resource: detail.resource || 'owner-device',
      operation: detail.operation || 'voice-request',
      purpose: detail.purpose || 'Owner voice request',
      request_text: detail.text.trim(),
      risks: Array.isArray(detail.risks) ? detail.risks : ['Voice input may be ambiguous.'],
      rewards: Array.isArray(detail.rewards) ? detail.rewards : ['Owner-controlled interaction.'],
      data_boundary: 'device-local-unless-explicitly-authorized'
    });
  };

  Integration.prototype.destroy = function () {
    this.closeSession().catch(function () {});
  };

  global.SGHV119DevAssist = Object.freeze({
    create: function (options) { return new Integration(options); },
    STATES: STATES,
    DECISIONS: DECISIONS
  });

  if (global.addEventListener) {
    global.addEventListener('sghv119:voice-command', function (event) {
      var runtime = global.SGHV119DevAssistRuntime;
      if (!runtime) return;
      runtime.handleVoiceCommand(event.detail).catch(function (error) {
        if (global.console && console.warn) console.warn('[SGHv119] voice request denied:', error.message);
      });
    });
  }
}(typeof window !== 'undefined' ? window : globalThis));
