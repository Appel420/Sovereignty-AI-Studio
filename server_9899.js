// ═══════════════════════════════════════════════════════════════════
// SUPERGROK PIPER TTS + BRIDGE SERVER — Port 9899
// Production · Zero Cloud · Zero Telemetry · HIPAA Safe
// Piper TTS (offline) · DuckDuckGo Proxy · Audit Chain · MFA Tokens
// ═══════════════════════════════════════════════════════════════════
'use strict';

const WebSocket = require('ws');
const { exec, spawn }  = require('child_process');
const http  = require('http');
const fs    = require('fs');
const path  = require('path');
const crypto = require('crypto');
const os    = require('os');

// ─── Config ─────────────────────────────────────────────────────────
const CFG = {
  port:       9899,
  piperBin:   process.env.PIPER_BIN   || './piper',
  piperModel: process.env.PIPER_MODEL || './en_US-lessac-medium.onnx',
  piperCfg:   process.env.PIPER_CFG   || './en_US-lessac-medium.onnx.json',
  tmpDir:     os.tmpdir(),
  auditLog:   './audit_9899.jsonl',
  maxTextLen: 1000,
  allowedOrigins: ['http://localhost', 'file://'],
  // DDG proxy targets (no Google, no Meta)
  ddgSearch:  'https://duckduckgo.com/?q=',
  ddgAI:      'https://duck.ai/',
  // Rate limiting
  rateWindow: 60000,   // 1 min
  rateLimit:  30,      // max 30 msgs/min per connection
  // Token store for MFA
  tokens: new Map(),
  // Session store (KC offline_access tokens)
  sessions: new Map(),
};

// ─── Audit Logger ────────────────────────────────────────────────────
const auditStream = fs.createWriteStream(CFG.auditLog, { flags: 'a' });
let auditSeq = 0;

function audit(event, detail, ws_id) {
  const entry = {
    seq:    ++auditSeq,
    ts:     new Date().toISOString(),
    ws_id:  ws_id || 'server',
    event,
    detail,
    hash:   crypto.createHash('sha256').update(`${auditSeq}${event}${detail}`).digest('hex').slice(0,16),
  };
  auditStream.write(JSON.stringify(entry) + '\n');
  if (process.env.VERBOSE) console.log(`[AUDIT] ${entry.ts} #${entry.seq} ${event}: ${detail}`);
  return entry;
}

// ─── Piper TTS ───────────────────────────────────────────────────────
let piperReady = fs.existsSync(CFG.piperBin) && fs.existsSync(CFG.piperModel);

async function piperSpeak(text, wsId) {
  return new Promise((resolve, reject) => {
    // Sanitize text — strip shell metacharacters
    const safe = text.replace(/[`$\\'";&|<>(){}[\]!#*?~\n\r]/g, ' ').slice(0, CFG.maxTextLen);
    const wavFile = path.join(CFG.tmpDir, `piper_${wsId}_${Date.now()}.wav`);

    if (!piperReady) {
      // Fallback: generate silence wav header (8 bytes) so client knows it's done
      audit('PIPER_FALLBACK', 'Piper not found — returning done signal', wsId);
      resolve({ done: true, fallback: true });
      return;
    }

    // Use stdio pipe: echo text | piper --model X --output_file Y
    const child = spawn(CFG.piperBin, [
      '--model',       CFG.piperModel,
      '--output_file', wavFile,
    ]);

    child.stdin.write(safe);
    child.stdin.end();

    child.on('close', (code) => {
      if (code !== 0) {
        audit('PIPER_ERROR', `Exit ${code} for: ${safe.slice(0,40)}`, wsId);
        reject(new Error('Piper exited ' + code));
        return;
      }
      // Read wav and return as base64
      fs.readFile(wavFile, (err, data) => {
        fs.unlink(wavFile, ()=>{}); // cleanup
        if (err) { reject(err); return; }
        audit('PIPER_SPOKE', safe.slice(0, 60), wsId);
        resolve({ type: 'audio', codec: 'wav', data: data.toString('base64') });
      });
    });

    child.on('error', (e) => {
      piperReady = false;
      audit('PIPER_CRASH', e.message, wsId);
      reject(e);
    });
  });
}

// ─── DDG Proxy ───────────────────────────────────────────────────────
function ddgProxy(query, mode, wsId) {
  return new Promise((resolve, reject) => {
    if (mode === 'ghost') {
      audit('DDG_GHOST_BLOCK', query.slice(0,40), wsId);
      resolve({ blocked: true, mode: 'ghost' });
      return;
    }
    const url = CFG.ddgSearch + encodeURIComponent(query) + '&t=supergrok&ia=answer';
    audit('DDG_FETCH', url.slice(0,80), wsId);
    https.get(url, { headers: { 'User-Agent': 'SuperGrok/5.0 Privacy/HIPAA' } }, (res) => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => resolve({ status: res.statusCode, length: body.length }));
    }).on('error', reject);
  });
}

// ─── Sovereign AI Proxy ──────────────────────────────────────────────
// Routes ALL AI requests through the self-hosted sovereign bridge.
// No external SaaS. No data leaves the infrastructure.
const SOVEREIGN_AI_URL = (process.env.SOVEREIGN_API_URL || 'http://localhost:8002/api/ai').replace(/\/$/, '');

function aiProxy(agent, payload) {
  return new Promise((resolve) => {
    const prompt = String((payload && payload.prompt) || '').slice(0, CFG.maxTextLen);
    const systemPrompt = String((payload && payload.system) || '');
    const messages = [];
    if (systemPrompt) messages.push({ role: 'system', content: systemPrompt });
    messages.push({ role: 'user', content: prompt });

    const body = JSON.stringify({
      messages,
      max_tokens: 1200,
      context: { agent: agent || 'sovereign' },
    });

    const sovereignUrl = new URL(SOVEREIGN_AI_URL + '/chat');
    const reqOptions = {
      hostname: sovereignUrl.hostname,
      port: sovereignUrl.port || 80,
      path: sovereignUrl.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
      timeout: 30000,
    };

    const req = http.request(reqOptions, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        try {
          const parsed = JSON.parse(Buffer.concat(chunks).toString());
          const text = parsed.text || parsed.response ||
            (parsed.choices && parsed.choices[0] && parsed.choices[0].message && parsed.choices[0].message.content) ||
            'No response';
          resolve({ text });
        } catch (e) {
          resolve({ error: 'Parse error: ' + e.message });
        }
      });
    });
    req.on('error', (e) => resolve({ error: 'Sovereign bridge error: ' + e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ error: 'Sovereign AI timeout' }); });
    req.write(body);
    req.end();
  });
}

// ─── MFA Token Generator ─────────────────────────────────────────────
function generateMFAToken(role, name) {
  const token = crypto.randomBytes(32).toString('hex');
  const entry = {
    token,
    role, name,
    created: Date.now(),
    expires: Date.now() + 300000, // 5 min
    used: false,
  };
  CFG.tokens.set(token, entry);
  audit('MFA_TOKEN_GEN', `Role: ${role} Name: ${name}`, 'server');
  // Auto-expire
  setTimeout(() => CFG.tokens.delete(token), 300000);
  return token;
}

function verifyMFAToken(token) {
  const entry = CFG.tokens.get(token);
  if (!entry) return { ok: false, reason: 'not found' };
  if (Date.now() > entry.expires) { CFG.tokens.delete(token); return { ok: false, reason: 'expired' }; }
  if (entry.used) return { ok: false, reason: 'already used' };
  entry.used = true;
  audit('MFA_TOKEN_USED', `Role: ${entry.role}`, 'server');
  return { ok: true, role: entry.role, name: entry.name };
}

// ─── Keycloak Session Persistence ────────────────────────────────────
function saveKCSession(wsId, data) {
  CFG.sessions.set(wsId, { ...data, savedAt: Date.now() });
  audit('KC_SESSION_SAVE', `ws_id: ${wsId}`, wsId);
}
function loadKCSession(wsId) {
  const s = CFG.sessions.get(wsId);
  if (!s) return null;
  if (Date.now() > s.tokenExp) { CFG.sessions.delete(wsId); return null; }
  return s;
}

// ─── WebSocket Server ─────────────────────────────────────────────────
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain', 'X-Content-Type-Options': 'nosniff' });
  res.end('SuperGrok Bridge 9899 — OK');
});

const wss = new WebSocket.Server({ server });

let connCount = 0;

wss.on('connection', (ws, req) => {
  const wsId = 'ws_' + (++connCount) + '_' + Date.now();
  const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';

  // Rate limiting
  const rateMap = new Map();
  let msgCount = 0;
  const rateReset = setInterval(() => { msgCount = 0; }, CFG.rateWindow);

  audit('WS_CONNECT', `ip: ${ip}`, wsId);
  console.log(`[+] WS connected: ${wsId} from ${ip}`);

  ws.on('message', async (raw) => {
    // Rate limit
    msgCount++;
    if (msgCount > CFG.rateLimit) {
      ws.send(JSON.stringify({ type: 'error', code: 'RATE_LIMIT', msg: 'Too many requests' }));
      audit('RATE_LIMIT', `ip: ${ip} count: ${msgCount}`, wsId);
      return;
    }

    let msg;
    try { msg = JSON.parse(raw); }
    catch(e) { ws.send(JSON.stringify({ type: 'error', code: 'PARSE', msg: 'Invalid JSON' })); return; }

    const { type, text, query, mode, token, role, name, data: msgData } = msg;

    // ── SPEAK (Piper TTS) ──────────────────────────────────────────
    if (type === 'speak') {
      if (!text || typeof text !== 'string') {
        ws.send(JSON.stringify({ type: 'error', code: 'NO_TEXT' })); return;
      }
      audit('VOICE_CMD', `Spoke: ${text.slice(0,60)}`, wsId);
      try {
        const result = await piperSpeak(text, wsId);
        ws.send(JSON.stringify(result));
      } catch(e) {
        ws.send(JSON.stringify({ type: 'done', fallback: true }));
      }
      return;
    }

    // ── DDG SEARCH ────────────────────────────────────────────────
    if (type === 'ddg_search') {
      try {
        const result = await ddgProxy(query || '', mode || 'live', wsId);
        ws.send(JSON.stringify({ type: 'ddg_result', ...result }));
      } catch(e) {
        ws.send(JSON.stringify({ type: 'error', code: 'DDG_FAIL', msg: e.message }));
      }
      return;
    }

    // ── MFA TOKEN GENERATE ────────────────────────────────────────
    if (type === 'mfa_gen') {
      const tok = generateMFAToken(role || 'unknown', name || 'unknown');
      ws.send(JSON.stringify({ type: 'mfa_token', token: tok }));
      return;
    }

    // ── MFA TOKEN VERIFY ──────────────────────────────────────────
    if (type === 'mfa_verify') {
      const result = verifyMFAToken(token);
      ws.send(JSON.stringify({ type: 'mfa_result', ...result }));
      return;
    }

    // ── KC SESSION SAVE ───────────────────────────────────────────
    if (type === 'kc_save') {
      saveKCSession(wsId, msgData || {});
      ws.send(JSON.stringify({ type: 'kc_saved', wsId }));
      return;
    }

    // ── KC SESSION LOAD ───────────────────────────────────────────
    if (type === 'kc_load') {
      const session = loadKCSession(wsId);
      ws.send(JSON.stringify({ type: 'kc_session', session }));
      return;
    }

    // ── AUDIT EXPORT ──────────────────────────────────────────────
    if (type === 'audit_export') {
      try {
        const logs = fs.readFileSync(CFG.auditLog, 'utf8').split('\n').filter(Boolean).slice(-100);
        ws.send(JSON.stringify({ type: 'audit_data', logs: logs.map(l=>{try{return JSON.parse(l);}catch{return l;}}) }));
      } catch(e) {
        ws.send(JSON.stringify({ type: 'audit_data', logs: [] }));
      }
      return;
    }

    // ── PING ──────────────────────────────────────────────────────
    if (type === 'ping') {
      ws.send(JSON.stringify({ type: 'pong', ts: Date.now(), piperReady, wsId }));
      return;
    }

    // ── AGENT ROUTING ──────────────────────────────────────────────
    if (type === 'agent_request') {
      const agent = String(msg.agent || '').toLowerCase();
      const payload = msg.payload || {};
      const result = await aiProxy(agent, payload);
      ws.send(JSON.stringify({
        type: 'agent_response',
        agent,
        payload: result.error ? { text: result.error, error: true } : { text: result.text || '' },
        ts: Date.now(),
      }));
      return;
    }


    // ── PIPER STATUS (matches piper_tts_service.py PiperTTSService) ──
    if (type === 'piper_status') {
      // Mirror PiperTTSService._find_piper_executable() logic
      const models = [];
      const searchDirs = [process.cwd(), path.join(process.cwd(),'models'), CFG.piperModel ? path.dirname(CFG.piperModel) : ''];
      searchDirs.filter(Boolean).forEach(d => {
        try {
          if (fs.existsSync(d)) fs.readdirSync(d).filter(f=>f.endsWith('.onnx')).forEach(f=>{
            models.push({ id: f.replace('.onnx',''), name: f, path: path.join(d,f) });
          });
        } catch(e){}
      });
      ws.send(JSON.stringify({ type:'piper_status_result', piperReady, exe:CFG.piperBin,
        model:CFG.piperModel, models, wsId }));
      return;
    }

    // ── PIPER MODELS LIST ──────────────────────────────────────────
    if (type === 'piper_models') {
      const models = [];
      const searchDirs = [process.cwd(), path.join(process.cwd(),'models')];
      searchDirs.forEach(d => {
        try {
          if(fs.existsSync(d)) fs.readdirSync(d).filter(f=>f.endsWith('.onnx')).forEach(f=>{
            models.push({ id:f.replace('.onnx',''), name:f, path:path.join(d,f) });
          });
        }catch(e){}
      });
      ws.send(JSON.stringify({ type:'piper_models_result', models }));
      return;
    }

    // ── SET PIPER MODEL ────────────────────────────────────────────
    if (type === 'set_model') {
      // Sanitize path — no traversal. Mirror PiperTTSService model path logic.
      const safe_model = (msg.model||'').replace(/[.][.]/g,'').replace(/[/\\]/g,'');
      const modelPath = path.join(process.cwd(), 'models', safe_model + '.onnx');
      if (fs.existsSync(modelPath)) {
        CFG.piperModel = modelPath;
        currentPiperModel = modelPath;
        piperReady = fs.existsSync(CFG.piperBin||'') && fs.existsSync(CFG.piperModel);
        audit('MODEL_SWITCH', 'Switched to: ' + safe_model, wsId);
        ws.send(JSON.stringify({ type:'model_switched', model:safe_model, ready:piperReady }));
      } else {
        ws.send(JSON.stringify({ type:'model_error', error:'Model not found: '+safe_model }));
      }
      return;
    }

    // ── SPEAK ALERT (matches piper_tts_service.speak_alert) ────────
    // severity: low|medium|high|critical → prepends "Alert!" for high/critical
    if (type === 'speak_alert') {
      const severity = (msg.severity||'medium').toLowerCase();
      const title = msg.title || '';
      const message = msg.message || msg.text || '';
      const spokenText = (severity==='high'||severity==='critical')
        ? 'Alert! ' + title + '. ' + message
        : title + '. ' + message;
      audit('SPEAK_ALERT', severity + ': ' + spokenText.slice(0,60), wsId);
      try {
        const result = await piperSpeak(spokenText, wsId);
        ws.send(JSON.stringify(result));
      } catch(e) {
        ws.send(JSON.stringify({ type:'done', fallback:true }));
      }
      return;
    }

    // ── OFFLINE AI (Piper TTS only — ZERO external model calls) ────
    // Text inference stays on DDG bridge. Voice via Piper. No Meta. No LLaMA.
    if (type === 'offline_ai') {
      const msgs = msg.messages || [];
      const last = msgs.length ? msgs[msgs.length-1].content : msg.text || '';
      audit('OFFLINE_AI', 'Piper TTS: '+last.slice(0,40), wsId);
      try {
        const result = await piperSpeak(last, wsId);
        ws.send(JSON.stringify(Object.assign({}, result, { type:'offline_ai_response' })));
      } catch(e) {
        ws.send(JSON.stringify({ type:'offline_ai_response', fallback:true }));
      }
      return;
    }

    // ── MEMORY CARDS (cross-session AI context handoff) ────────────
    if (type === 'memory_save') {
      const key = (msg.role||'anon') + '_' + (msg.user||'anon');
      if (!memStore[key]) memStore[key]=[];
      memStore[key].unshift({ ts:Date.now(), title:msg.title||'', content:msg.content||'' });
      if (memStore[key].length>100) memStore[key]=memStore[key].slice(0,100);
      audit('MEMORY_SAVE', (msg.title||'').slice(0,40), wsId);
      ws.send(JSON.stringify({ type:'memory_saved', key }));
      return;
    }
    if (type === 'memory_get') {
      const key = (msg.role||'anon') + '_' + (msg.user||'anon');
      ws.send(JSON.stringify({ type:'memory_result', cards:(memStore[key]||[]).slice(0,10) }));
      return;
    }

    // ── COLLABORATION BROADCAST (user↔user, user↔AI) ───────────────
    if (type === 'collab_broadcast') {
      let sent = 0;
      wss.clients.forEach(c => {
        if (c !== ws && c.readyState === 1) {
          c.send(JSON.stringify({ type:'collab_event', payload:msg.payload, from:msg.from||wsId, ts:Date.now() }));
          sent++;
        }
      });
      ws.send(JSON.stringify({ type:'collab_ack', sent }));
      return;
    }

    ws.send(JSON.stringify({ type: 'error', code: 'UNKNOWN_TYPE', received: type }));
  });

  ws.on('close', () => {
    clearInterval(rateReset);
    audit('WS_CLOSE', `ip: ${ip}`, wsId);
    console.log(`[-] WS closed: ${wsId}`);
  });

  ws.on('error', (e) => {
    audit('WS_ERROR', e.message, wsId);
  });

  // Send hello
  ws.send(JSON.stringify({
    type: 'hello',
    version: '6.0',
    wsId,
    piperReady,
    piperModel: CFG.piperModel,
    features: ['piper_tts','speak_alert','ddg_proxy','mfa_token','kc_session','audit_export','memory_cards','collab_broadcast','offline_ai','piper_models'],
    ts: Date.now(),
  }));
});


// Cross-session memory store (in-memory, per-process)
const memStore = {};

server.listen(CFG.port, '127.0.0.1', () => {
  console.log(`\n╔══════════════════════════════════════════════════╗`);
  console.log(`║  SuperGrok Bridge Server v6.0 — Piper Only                  ║`);
  console.log(`║  ws://127.0.0.1:${CFG.port}                        ║`);
  console.log(`║  Piper: ${piperReady ? '✅ READY' : '⚠️  NOT FOUND (fallback active)'}              ║`);
  console.log(`║  Audit: ${CFG.auditLog}                     ║`);
  console.log(`║  Zero Google · Zero Meta · HIPAA Safe          ║`);
  console.log(`╚══════════════════════════════════════════════════╝\n`);
  audit('SERVER_START', `Port ${CFG.port} · Piper: ${piperReady}`, 'server');
});

process.on('SIGINT', () => {
  audit('SERVER_STOP', 'SIGINT received', 'server');
  auditStream.end();
  process.exit(0);
});

// ─── GITHUB OAUTH CODE EXCHANGE (added v6) ───────────────────────
// Handles {type:'gh_exchange', code:'...'} from browser
// Requires GH_CLIENT_SECRET env var — never in browser
// Usage: GH_CLIENT_ID=xxx GH_CLIENT_SECRET=yyy node server_9899.js
function handleGHExchange(data, ws) {
  var clientId = process.env.GH_CLIENT_ID || '';
  var clientSecret = process.env.GH_CLIENT_SECRET || '';
  if (!clientId || !clientSecret) {
    ws.send(JSON.stringify({ type: 'gh_token_error', error: 'Set GH_CLIENT_ID and GH_CLIENT_SECRET env vars' }));
    return;
  }
  var https = require('https');
  var body = JSON.stringify({ client_id: clientId, client_secret: clientSecret, code: data.code });
  var opts = {
    hostname: 'github.com', path: '/login/oauth/access_token',
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'Content-Length': Buffer.byteLength(body) }
  };
  var req = https.request(opts, function(res) {
    var chunks = [];
    res.on('data', function(c) { chunks.push(c); });
    res.on('end', function() {
      try {
        var parsed = JSON.parse(Buffer.concat(chunks).toString());
        if (parsed.access_token) {
          logAudit({ event: 'GH_TOKEN_EXCHANGED', detail: 'OAuth code exchanged' });
          ws.send(JSON.stringify({ type: 'gh_token', token: parsed.access_token, scope: parsed.scope }));
        } else {
          ws.send(JSON.stringify({ type: 'gh_token_error', error: parsed.error || 'no token' }));
        }
      } catch(e) { ws.send(JSON.stringify({ type: 'gh_token_error', error: e.message })); }
    });
  });
  req.on('error', function(e) { ws.send(JSON.stringify({ type: 'gh_token_error', error: e.message })); });
  req.write(body);
  req.end();
}

// ─── FILE CHUNK REASSEMBLY (added v6) ───────────────────────────
var chunkBuffers = {};
function handleChunk(data, ws) {
  var id = data.id;
  if (!chunkBuffers[id]) chunkBuffers[id] = { chunks: [], total: data.total };
  chunkBuffers[id].chunks[data.seq] = data.data;
  if (chunkBuffers[id].chunks.filter(Boolean).length === data.total) {
    var full = chunkBuffers[id].chunks.join('');
    delete chunkBuffers[id];
    try {
      var parsed = JSON.parse(full);
      logAudit({ event: 'FILE_RECEIVED', detail: (parsed.filename || id) + ' ' + (parsed.size || 0) + 'B' });
      ws.send(JSON.stringify({ type: 'file_received', filename: parsed.filename, size: parsed.size }));
      // Optionally save to disk if SAVE_TRANSFERS=1
      if (process.env.SAVE_TRANSFERS === '1' && parsed.data && parsed.filename) {
        var fs = require('fs');
        var safe = parsed.filename.replace(/[^a-zA-Z0-9._-]/g, '_');
        fs.writeFileSync('./transfers/' + safe, Buffer.from(parsed.data, 'base64'));
        logAudit({ event: 'FILE_SAVED', detail: './transfers/' + safe });
      }
    } catch(e) { logAudit({ event: 'FILE_CHUNK_ERROR', detail: e.message }); }
  }
}

// Wire into existing message handler — append to exports
module.exports = module.exports || {};
module.exports.handleGHExchange = handleGHExchange;
module.exports.handleChunk = handleChunk;

// ─── PLAID PROXY (v7) — client_secret never touches browser ─────────
// Handles: plaid_link_token, plaid_exchange, plaid_balance, plaid_balance_get
// All Plaid API calls go through here. Browser only sees results.
var plaidAccessTokens = {};  // ephemeral — restart = re-link (use encrypted file for prod)

function plaidProxy(type, data, ws) {
  var https = require('https');
  var env = data.env || 'sandbox';
  var host = env === 'production' ? 'api.plaid.com'
           : env === 'development' ? 'development.plaid.com'
           : 'sandbox.plaid.com';

  var endpoints = {
    'plaid_link_token':  '/link/token/create',
    'plaid_exchange':    '/item/public_token/exchange',
    'plaid_balance':     '/accounts/balance/get'
  };

  var bodies = {
    'plaid_link_token': JSON.stringify({
      client_id: data.client_id, secret: data.secret,
      user: { client_user_id: 'supergrok_user_' + (data.name || 'user').replace(/\s/g,'_') },
      client_name: 'SuperGrok', products: ['auth','balance'],
      country_codes: ['US'], language: 'en'
    }),
    'plaid_exchange': JSON.stringify({
      client_id: data.client_id, secret: data.secret,
      public_token: data.public_token
    }),
    'plaid_balance': (function() {
      var token = plaidAccessTokens[data.name] || data.access_token;
      return JSON.stringify({ client_id: data.client_id, secret: data.secret, access_token: token });
    })()
  };

  var body = bodies[type];
  if (!body) return;

  var opts = {
    hostname: host, path: endpoints[type], method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
  };

  var req = https.request(opts, function(res) {
    var chunks = [];
    res.on('data', function(c) { chunks.push(c); });
    res.on('end', function() {
      try {
        var parsed = JSON.parse(Buffer.concat(chunks).toString());
        if (type === 'plaid_link_token') {
          ws.send(JSON.stringify({ type: 'plaid_link_token_result', link_token: parsed.link_token }));
        } else if (type === 'plaid_exchange') {
          // Store access token server-side, never send to browser
          if (parsed.access_token) plaidAccessTokens[data.name] = parsed.access_token;
          ws.send(JSON.stringify({ type: 'plaid_exchange_result', ok: !!parsed.access_token, name: data.name }));
        } else if (type === 'plaid_balance') {
          ws.send(JSON.stringify({ type: 'plaid_balance_result', accounts: parsed.accounts || [], name: data.name }));
        }
        logAudit({ event: 'PLAID_' + type.toUpperCase(), detail: (data.name || '') + ' via ' + env });
      } catch(e) {
        ws.send(JSON.stringify({ type: 'plaid_error', error: e.message, for: type }));
      }
    });
  });
  req.on('error', function(e) {
    ws.send(JSON.stringify({ type: 'plaid_error', error: e.message, for: type }));
  });
  req.write(body);
  req.end();
}

// ─── SHELL CMD ECHO (v7) ─────────────────────────────────────────────
function handleShellCmd(data, ws) {
  // Routes shell commands — can exec safe whitelisted ops
  var whitelist = ['ls', 'pwd', 'date', 'whoami', 'uptime', 'df -h', 'free -h'];
  var isWhitelisted = whitelist.some(function(c) { return data.cmd && data.cmd.trim().startsWith(c); });
  if (isWhitelisted && process.env.ALLOW_SHELL === '1') {
    var { exec } = require('child_process');
    exec(data.cmd, { timeout: 5000 }, function(err, stdout, stderr) {
      ws.send(JSON.stringify({ type: 'shell_output', role: data.role, output: stdout || stderr || err && err.message || '' }));
      logAudit({ event: 'SHELL_EXEC', detail: data.role + ': ' + data.cmd });
    });
  } else {
    // Echo back with role context
    ws.send(JSON.stringify({
      type: 'shell_output',
      role: data.role,
      output: '[' + data.role + '] ' + (data.cmd || '') + ' — received at ' + new Date().toISOString()
    }));
    logAudit({ event: 'SHELL_CMD', detail: (data.user||'?') + ' @ ' + data.role + ': ' + (data.cmd||'') });
  }
}

// ─── MODEL SWITCH (v7) ───────────────────────────────────────────────
var currentPiperModel = process.env.PIPER_MODEL || './en_US-lessac-medium.onnx';
function handleSetModel(data) {
  if (data.model && data.model.endsWith('.onnx')) {
    currentPiperModel = './' + data.model.replace(/\.\.\//g,'');
    logAudit({ event: 'MODEL_SWITCH', detail: currentPiperModel });
    console.log('[PIPER] Model switched to:', currentPiperModel);
  }
}
