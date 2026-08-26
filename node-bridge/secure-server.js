#!/usr/bin/env node
'use strict';

const fs = require('fs');
const https = require('https');
const http = require('http');

const cert = process.env.TLS_CERT;
const key = process.env.TLS_KEY;
if (!cert || !key) throw new Error('TLS_CERT and TLS_KEY are required; refusing plaintext Node bridge startup');
if (!fs.existsSync(cert) || !fs.existsSync(key)) throw new Error(`TLS material missing: ${cert} / ${key}`);

const tlsOptions = { cert: fs.readFileSync(cert), key: fs.readFileSync(key), minVersion: 'TLSv1.3' };
const originalCreateServer = http.createServer;
http.createServer = function secureCreateServer(requestListener) {
  return https.createServer(tlsOptions, requestListener);
};
process.env.SG_TLS_MODE = 'https-wss';
require('./server.js');
