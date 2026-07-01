'use strict';

/**
 * SGHV119 E2EE Middleware
 *
 * Express helper for HTTPS request/response routes.
 * This intentionally avoids browser ws:// control traffic.
 *
 * Requires:
 *   SGHV119_E2EE_BOOTSTRAP_SECRET=<32+ chars>
 *
 * Request shape from SGHV119.html:
 *   Header: X-SGHV119-E2EE: quad-ratchet-v1
 *   Body:   { encrypted: true, envelope: {...} }
 */

const QR = require('./e2ee_quad_ratchet_node');

const E2EE_HEADER = 'x-sghv119-e2ee';
const E2EE_HEADER_VALUE = 'quad-ratchet-v1';

function isEncryptedRequest(req) {
  return String(req.headers[E2EE_HEADER] || '').toLowerCase() === E2EE_HEADER_VALUE;
}

async function unwrapRequest(req) {
  if (!isEncryptedRequest(req)) {
    return {
      encrypted: false,
      plaintext: req.body || {},
      state: null,
      envelope: null,
    };
  }

  const secret = process.env.SGHV119_E2EE_BOOTSTRAP_SECRET || '';
  if (!secret || secret.length < 32) {
    const err = new Error('E2EE bootstrap secret is not configured');
    err.statusCode = 503;
    throw err;
  }

  const body = req.body || {};
  if (body.encrypted !== true || !body.envelope) {
    const err = new Error('Invalid encrypted SGHV119 request body');
    err.statusCode = 400;
    throw err;
  }

  const state = await QR.serverStateForEnvelope(body.envelope, secret);
  const plaintext = await QR.decryptClientEnvelope(state, body.envelope);

  return {
    encrypted: true,
    plaintext,
    state,
    envelope: body.envelope,
  };
}

async function wrapResponse(context, plaintextResponse, routeMeta) {
  if (!context || !context.encrypted) {
    return plaintextResponse;
  }

  const envelope = await QR.encryptServerEnvelope(context.state, plaintextResponse, routeMeta || {});
  return {
    encrypted: true,
    envelope,
  };
}

function sendE2eeError(res, err) {
  const status = err.statusCode || 400;
  res.status(status).json({
    encrypted: false,
    error: 'SGHV119_E2EE_ERROR',
    message: err.message,
    timestamp: new Date().toISOString(),
  });
}

module.exports = {
  E2EE_HEADER,
  E2EE_HEADER_VALUE,
  isEncryptedRequest,
  unwrapRequest,
  wrapResponse,
  sendE2eeError,
};
