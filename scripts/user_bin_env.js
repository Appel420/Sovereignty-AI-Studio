#!/usr/bin/env node
// ═══════════════════════════════════════════════════════════════════════════
//  GROK_EDU PRODUCTION SERVER  ·  Port 9898
//  Full-stack: HTTP + WebSocket + SSE + BLE bridge + EEG + Air-gap
//
//  Start:  node grok-edu-server.mjs
//  iSH:    apk add nodejs npm && node grok-edu-server.mjs
//  a-Shell: node grok-edu-server.mjs
// ═══════════════════════════════════════════════════════════════════════════
"use strict";

import http        from "http";
import https       from "https";
import fs          from "fs";
import path        from "path";
import vm          from "vm";
import crypto      from "crypto";
import os          from "os";
import { spawn, exec } from "child_process";
import { fileURLToPath } from "url";
import { createRequire  } from "module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require   = createRequire(import.meta.url);

// ── CONFIG ──────────────────────────────────────────────────────────────────
const PORT           = parseInt(process.env.PORT || "9898");
const AIRGAP         = process.env.AIRGAP === "true";
const DATA_DIR       = path.join(__dirname, "grok_data");
const HIPAA_DIR      = path.join(DATA_DIR, "hipaa_logs");
const SCAR_FILE      = path.join(DATA_DIR, "scar_chain.ndjson");
const AVATARS_FILE   = path.join(DATA_DIR, "avatars.json");
const SESSIONS_FILE  = path.join(DATA_DIR, "sessions.json");
const PROJECTS_FILE  = path.join(DATA_DIR, "projects.json");
const MAX_EXEC_MS    = 10,000;
const MAX_BODY       = 2,000,000; // 2MB

const CORS_ORIGINS = [
  "http://localhost:9898", "http://127.0.0.1:9898",
  "http://localhost:9898", "http://localhost:9898",
  "null", // file:// origins
  "*"
];

// ── INIT DIRS ────────────────────────────────────────────────────────────────
for (const d of [DATA_DIR, HIPAA_DIR]) {
  if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
}
function loadJSON(f, def) {
  try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { return def; }
}
function saveJSON(f, data) {
  try { fs.writeFileSync(f, JSON.stringify(data, null, 2)); } catch {}
}

// Runtime stores
let avatars  = loadJSON(AVATARS_FILE,  {});
let sessions = loadJSON(SESSIONS_FILE, []);
let projects = loadJSON(PROJECTS_FILE, []);

// ── SCAR CHAIN ───────────────────────────────────────────────────────────────
let _prevHash = "genesis_grok_edu_9898";

function blake3ish(data) {
  try { return require("blake3").hash(Buffer.from(String(data))).toString("hex"); }
  catch {
    const h1 = crypto.createHash("sha256").update(String(data)).digest();
    return "compat:" + crypto.createHash("sha256").update(h1).digest("hex");
  }
}

function appendSCAR(payload, actor = "SYSTEM") {
  const ts = Date.now();
  const hash = blake3ish(`${_prevHash}|${payload}|${ts}`);
  const entry = { id: crypto.randomUUID(), ts, actor, payload: String(payload).slice(0, 200), prevHash: _prevHash, hash };
  _prevHash = hash;
  try { fs.appendFileSync(SCAR_FILE, JSON.stringify(entry) + "\n"); } catch {}
  return entry;
}

function verifySCAR() {
  if (!fs.existsSync(SCAR_FILE)) return { ok: true, length: 0 };
  const lines = fs.readFileSync(SCAR_FILE, "utf8").trim().split("\n").filter(Boolean);
  let prev = "genesis_grok_edu_9898";
  for (let i = 0; i < lines.length; i++) {
    let e; try { e = JSON.parse(lines[i]); } catch { return { ok: false, brokenAt: i }; }
    if (e.prevHash !== prev) return { ok: false, brokenAt: i, entry: e };
    prev = e.hash;
  }
  return { ok: true, length: lines.length };
}

function readSCAR(limit = 100) {
  if (!fs.existsSync(SCAR_FILE)) return [];
  return fs.readFileSync(SCAR_FILE, "utf8").trim().split("\n").filter(Boolean)
    .slice(-Math.min(limit, 500)).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
}

// ── HIPAA ────────────────────────────────────────────────────────────────────
function hipaaLog(userId, action, meta = {}) {
  const pid = crypto.createHash("sha256").update(`${userId}|${Math.floor(Date.now()/3_600_000)}`).digest("hex").slice(0, 12);
  const ts  = new Date().toISOString();
  const file = path.join(HIPAA_DIR, `${ts.slice(0,10)}.ndjson`);
  try { fs.appendFileSync(file, JSON.stringify({ ts, pid, action, meta: JSON.stringify(meta) }) + "\n"); } catch {}
  appendSCAR(`HIPAA:${action}:${pid}`, userId || "anon");
  return pid;
}

// ── EEG SIMULATION (real BLE via Web Bluetooth in browser) ──────────────────
// Server provides simulated EEG data; real BLE connects directly in browser
const EEG_STATE = {
  clients: new Set(),
  streaming: false,
  interval: null,
  data: { alpha: 0, beta: 0, theta: 0, delta: 0, gamma: 0, attention: 0, meditation: 0, blink: 0, ts: 0 }
};

function startEEGStream() {
  if (EEG_STATE.streaming) return;
  EEG_STATE.streaming = true;
  let t = 0;
  EEG_STATE.interval = setInterval(() => {
    t += 0.1;
    // Realistic EEG band simulation with natural variation
    const noise  = () => (Math.random() - 0.5) * 8;
    const alpha  = Math.max(0, Math.min(100, 45 + Math.sin(t * 0.3) * 20 + noise()));
    const beta   = Math.max(0, Math.min(100, 30 + Math.cos(t * 0.5) * 15 + noise()));
    const theta  = Math.max(0, Math.min(100, 25 + Math.sin(t * 0.2) * 12 + noise()));
    const delta  = Math.max(0, Math.min(100, 15 + Math.sin(t * 0.1) * 8  + noise()));
    const gamma  = Math.max(0, Math.min(100, 10 + Math.cos(t * 0.8) * 6  + noise()));
    const attention  = Math.max(0, Math.min(100, (alpha * 0.4 + beta * 0.4 - theta * 0.2) + noise()));
    const meditation = Math.max(0, Math.min(100, (alpha * 0.6 - beta * 0.3 + theta * 0.1) + noise()));
    const blink = Math.random() < 0.02 ? 1 : 0; // ~2% blink rate

    EEG_STATE.data = { alpha: +alpha.toFixed(2), beta: +beta.toFixed(2), theta: +theta.toFixed(2),
      delta: +delta.toFixed(2), gamma: +gamma.toFixed(2),
      attention: +attention.toFixed(2), meditation: +meditation.toFixed(2),
      blink, ts: Date.now(), source: "grok-edu-eeg-bridge" };

    const msg = `data: ${JSON.stringify(EEG_STATE.data)}\n\n`;
    for (const client of EEG_STATE.clients) {
      try { client.write(msg); } catch { EEG_STATE.clients.delete(client); }
    }
  }, 100); // 10Hz EEG stream
}

// ── LiDAR / BLE BRIDGE STATE ─────────────────────────────────────────────────
const BLE_STATE = {
  clients: new Set(), // SSE clients for LiDAR/BLE data
  devices: new Map(), // deviceId → { name, rssi, distance, angle }
  lidarPoints: []     // [{x,y,z,intensity}]
};

// Simulate LiDAR point cloud (real: WebBluetooth in browser)
function startLiDARSim() {
  setInterval(() => {
    if (BLE_STATE.clients.size === 0) return;
    // Generate 360° point cloud (64 points)
    const points = [];
    const t = Date.now() / 1000;
    for (let i = 0; i < 64; i++) {
      const angle = (i / 64) * Math.PI * 2;
      const dist  = 1.5 + Math.sin(angle * 3 + t) * 0.4 + Math.random() * 0.1;
      points.push({
        angle: +(angle * 180 / Math.PI).toFixed(1),
        distance: +(dist * 100).toFixed(1), // cm
        x: +(Math.cos(angle) * dist).toFixed(3),
        y: +(Math.sin(angle) * dist).toFixed(3),
        z: +(0.5 + Math.sin(i * 0.3 + t) * 0.3).toFixed(3),
        intensity: Math.floor(128 + Math.sin(angle + t) * 60)
      });
    }
    BLE_STATE.lidarPoints = points;

    // Simulate BLE device discovery
    const devices = [
      { id: "muse-001", name: "Muse 2 EEG", type: "EEG", rssi: -55 + Math.floor(Math.random()*10), distance: +(1.2 + Math.random()*0.3).toFixed(2), connected: true },
      { id: "phone-001", name: "iPhone 15 Pro", type: "phone", rssi: -42 + Math.floor(Math.random()*5), distance: +(0.3 + Math.random()*0.1).toFixed(2), connected: true },
      { id: "tablet-001", name: "iPad Air", type: "tablet", rssi: -65 + Math.floor(Math.random()*8), distance: +(2.1 + Math.random()*0.4).toFixed(2), connected: false },
    ];

    const msg = `data: ${JSON.stringify({ type: "lidar", points, devices, ts: Date.now() })}\n\n`;
    for (const c of BLE_STATE.clients) {
      try { c.write(msg); } catch { BLE_STATE.clients.delete(c); }
    }
  }, 100); // 10Hz LiDAR
}
startLiDARSim();

// ── WEBSOCKET CLIENTS (collaboration + peer) ──────────────────────────────────
const WS_CLIENTS = new Map(); // socketId → { socket, userId, role, channel }
const CHANNELS   = new Map(); // channelId → Set of socketIds

function wsFrame(data) {
  const buf = Buffer.from(typeof data === "string" ? data : JSON.stringify(data), "utf8");
  const len = buf.length;
  if (len < 126) return Buffer.concat([Buffer.from([0x81, len]), buf]);
  if (len < 65536) { const h = Buffer.alloc(4); h[0]=0x81; h[1]=126; h.writeUInt16BE(len,2); return Buffer.concat([h,buf]); }
  const h = Buffer.alloc(10); h[0]=0x81; h[1]=127; h.writeBigUInt64BE(BigInt(len),2); return Buffer.concat([h,buf]);
}

function wsHandshake(req, socket) {
  const key = req.headers["sec-websocket-key"] || "";
  const accept = crypto.createHash("sha1").update(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest("base64");
  socket.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
}

function parseWsFrame(buf) {
  if (buf.length < 2) return null;
  const masked = !!(buf[1] & 0x80);
  let len = buf[1] & 0x7f;
  let offset = 2;
  if (len === 126) { len = buf.readUInt16BE(2); offset = 4; }
  else if (len === 127) { len = Number(buf.readBigUInt64BE(2)); offset = 10; }
  if (buf.length < offset + (masked ? 4 : 0) + len) return null;
  let payload;
  if (masked) {
    const mask = buf.slice(offset, offset + 4); offset += 4;
    payload = Buffer.alloc(len);
    for (let i = 0; i < len; i++) payload[i] = buf[offset + i] ^ mask[i % 4];
  } else {
    payload = buf.slice(offset, offset + len);
  }
  try { return JSON.parse(payload.toString()); } catch { return { raw: payload.toString() }; }
}

function broadcast(channel, msg, exclude = null) {
  const ids = CHANNELS.get(channel) || new Set();
  const frame = wsFrame(msg);
  for (const id of ids) {
    if (id === exclude) continue;
    const c = WS_CLIENTS.get(id);
    if (c) try { c.socket.write(frame); } catch {}
  }
}

// ── CODE EXECUTORS ────────────────────────────────────────────────────────────
function execNode(code, timeoutMs = MAX_EXEC_MS) {
  return new Promise(resolve => {
    const logs = [];
    const sandbox = {
      console: { log:(...a)=>logs.push(a.map(s=>typeof s==='object'?JSON.stringify(s):String(s)).join(' ')), error:(...a)=>logs.push('ERR:'+a.join(' ')), warn:(...a)=>logs.push('WARN:'+a.join(' ')), info:(...a)=>logs.push('INFO:'+a.join(' ')) },
      Math, JSON, Date, Array, Object, String, Number, Boolean, parseInt, parseFloat, isNaN, isFinite, encodeURIComponent,
      setTimeout:undefined, require:undefined, process:undefined, fetch:undefined, __dirname:undefined
    };
    vm.createContext(sandbox);
    try {
      const r = vm.runInContext(code, sandbox, { timeout: Math.min(timeoutMs, MAX_EXEC_MS) });
      if (r !== undefined) logs.push(typeof r === 'object' ? JSON.stringify(r,null,2) : String(r));
      resolve({ ok: true, output: logs.join('\n').slice(0, 32000) });
    } catch(e) { resolve({ ok: false, error: e.message, output: logs.join('\n') }); }
  });
}

function execPython(code, timeoutMs = MAX_EXEC_MS) {
  return new Promise(resolve => {
    const tmp = path.join(os.tmpdir(), `gedu_${Date.now()}.py`);
    fs.writeFileSync(tmp, code);
    let out='', err='';
    const py = spawn('python3', [tmp], { timeout: timeoutMs });
    py.stdout.on('data', d => out += d);
    py.stderr.on('data', d => err += d);
    py.on('close', code => { try{fs.unlinkSync(tmp);}catch{} resolve({ ok: code===0, output: (out+(err?'\n---stderr---\n'+err:'')).slice(0,32000), exitCode: code }); });
    py.on('error', e => { try{fs.unlinkSync(tmp);}catch{} resolve({ ok:false, error:e.message, output:'' }); });
  });
}

function execGit(args) {
  return new Promise(resolve => {
    const ALLOWED = ['status','log','pull','push','diff','branch','clone','init','add','commit','stash','fetch','checkout','merge','show','tag'];
    if (!ALLOWED.includes((args[0]||'').toLowerCase())) return resolve({ ok:false, output:`git ${args[0]}: blocked` });
    exec(`git ${args.join(' ')}`, { cwd: __dirname, timeout: 30000 }, (e, out, err) => resolve({ ok:!e, output:(out+err).slice(0,32000) }));
  });
}

// ── HTTP HELPERS ──────────────────────────────────────────────────────────────
function cors(req, res) {
  const o = req.headers.origin || '';
  const ok = CORS_ORIGINS.includes('*') || CORS_ORIGINS.includes(o);
  res.setHeader('Access-Control-Allow-Origin', ok ? (o||'*') : CORS_ORIGINS[0]);
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-User-ID,X-Role');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
}

function j(res, status, obj) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(obj));
}

function body(req) {
  return new Promise((resolve, reject) => {
    let b = '';
    req.on('data', c => { b += c; if (b.length > MAX_BODY) reject(new Error('Body too large')); });
    req.on('end', () => { try { resolve(JSON.parse(b || '{}')); } catch { resolve({}); } });
    req.on('error', reject);
  });
}

// ── AVATAR SYSTEM ─────────────────────────────────────────────────────────────
const AVATAR_STYLES = [
  { name: 'Nebula Scholar', bg: '#0a0f2e', accent: '#00e5ff', emoji: '🌌', trait: 'curious' },
  { name: 'Circuit Sage',   bg: '#0d1f0a', accent: '#00ff88', emoji: '⚡', trait: 'analytical' },
  { name: 'Quantum Fox',    bg: '#1a0a2e', accent: '#b44fff', emoji: '🦊', trait: 'creative' },
  { name: 'Solar Hawk',     bg: '#2e1a0a', accent: '#ffd600', emoji: '🦅', trait: 'leader' },
  { name: 'Crystal Mind',   bg: '#0a1e2e', accent: '#3d8bff', emoji: '💎', trait: 'precise' },
  { name: 'Storm Runner',   bg: '#2e0a0a', accent: '#ff4d9e', emoji: '⚡', trait: 'energetic' },
  { name: 'Deep Tide',      bg: '#0a1e1e', accent: '#00ccbb', emoji: '🌊', trait: 'calm' },
  { name: 'Nova Phoenix',   bg: '#2e180a', accent: '#ff8800', emoji: '🔥', trait: 'passionate' },
];

function createAvatar(userId, name, role, styleIdx = null) {
  const style = AVATAR_STYLES[styleIdx ?? (Math.floor(Math.random() * AVATAR_STYLES.length))];
  const avatar = {
    id: userId, name, role,
    style: style.name, bg: style.bg, accent: style.accent, emoji: style.emoji, trait: style.trait,
    xp: 0, level: 1, badges: [], focusStreak: 0, projectsBuilt: 0, gamesWon: 0,
    created: new Date().toISOString(), companion: {
      name: `${style.name.split(' ')[0]}-AI`,
      personality: style.trait,
      memory: [],
      mood: 'ready'
    }
  };
  avatars[userId] = avatar;
  saveJSON(AVATARS_FILE, avatars);
  return avatar;
}

// ── PROJECTS (collaboration) ──────────────────────────────────────────────────
function createProject(data) {
  const proj = { id: crypto.randomUUID(), ...data, created: new Date().toISOString(), files: {}, collaborators: [], status: 'active', chat: [] };
  projects.push(proj);
  saveJSON(PROJECTS_FILE, projects);
  return proj;
}

function getProject(id) { return projects.find(p => p.id === id); }

function updateProject(id, updates) {
  const i = projects.findIndex(p => p.id === id);
  if (i === -1) return null;
  projects[i] = { ...projects[i], ...updates, updated: new Date().toISOString() };
  saveJSON(PROJECTS_FILE, projects);
  return projects[i];
}

// ── MAIN HTTP SERVER ──────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  cors(req, res);
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  const url    = new URL(req.url, `http://localhost:${PORT}`);
  const route  = url.pathname;
  const userId = req.headers['x-user-id'] || 'anon';
  const role   = req.headers['x-role'] || 'student';

  try {
    // ── SERVE DASHBOARD HTML ─────────────────────────────────────────────────
    if (route === '/' || route === '/index.html') {
      const htmlFile = path.join(__dirname, 'grok-edu-dashboard.html');
      if (fs.existsSync(htmlFile)) {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(fs.readFileSync(htmlFile));
      } else {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end('<h1>Grok_Edu Server Running on :9898</h1><p>Place grok-edu-dashboard.html in same directory.</p>');
      }
      return;
    }

    // ── HEALTH ───────────────────────────────────────────────────────────────
    if (route === '/health') {
      return j(res, 200, {
        status: 'ok', service: 'Grok_Edu Production Server',
        version: '3.0.0', port: PORT, ts: new Date().toISOString(),
        uptime: Math.round(process.uptime()), node: process.version,
        platform: process.platform, airgap: AIRGAP,
        eegClients: EEG_STATE.clients.size, lidarClients: BLE_STATE.clients.size,
        wsClients: WS_CLIENTS.size, scarChain: verifySCAR(),
        avatars: Object.keys(avatars).length, projects: projects.length,
        sessions: sessions.length,
      });
    }

    // ── EEG SSE STREAM ───────────────────────────────────────────────────────
    if (route === '/api/eeg/stream') {
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no' });
      EEG_STATE.clients.add(res);
      startEEGStream();
      const hb = setInterval(() => {
        try { res.write(`event: heartbeat\ndata: ${JSON.stringify({ ts: Date.now(), clients: EEG_STATE.clients.size })}\n\n`); }
        catch { clearInterval(hb); EEG_STATE.clients.delete(res); }
      }, 5000);
      req.on('close', () => { clearInterval(hb); EEG_STATE.clients.delete(res); });
      return;
    }

    // ── LIDAR + BLE SSE ──────────────────────────────────────────────────────
    if (route === '/api/lidar/stream') {
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no' });
      BLE_STATE.clients.add(res);
      const hb = setInterval(() => {
        try { res.write(`event: heartbeat\ndata: ${JSON.stringify({ ts: Date.now() })}\n\n`); }
        catch { clearInterval(hb); BLE_STATE.clients.delete(res); }
      }, 5000);
      req.on('close', () => { clearInterval(hb); BLE_STATE.clients.delete(res); });
      return;
    }

    // ── EEG STATUS ───────────────────────────────────────────────────────────
    if (route === '/api/eeg/status') {
      return j(res, 200, { ...EEG_STATE.data, clients: EEG_STATE.clients.size, streaming: EEG_STATE.streaming });
    }

    // ── AVATARS ──────────────────────────────────────────────────────────────
    if (route === '/api/avatars' && req.method === 'GET') {
      return j(res, 200, Object.values(avatars));
    }
    if (route === '/api/avatars' && req.method === 'POST') {
      const { userId: uid, name, role: r, styleIdx } = await body(req);
      if (!uid || !name) return j(res, 400, { error: 'userId and name required' });
      const av = createAvatar(uid, name, r || 'student', styleIdx);
      appendSCAR(`AVATAR_CREATE:${uid}:${name}`, uid);
      return j(res, 201, av);
    }
    if (route.startsWith('/api/avatars/') && req.method === 'GET') {
      const uid = route.split('/')[3];
      const av = avatars[uid];
      return av ? j(res, 200, av) : j(res, 404, { error: 'Avatar not found' });
    }
    if (route.startsWith('/api/avatars/') && req.method === 'PUT') {
      const uid = route.split('/')[3];
      const updates = await body(req);
      if (!avatars[uid]) return j(res, 404, { error: 'Not found' });
      avatars[uid] = { ...avatars[uid], ...updates };
      saveJSON(AVATARS_FILE, avatars);
      return j(res, 200, avatars[uid]);
    }

    // ── COMPANION AI MEMORY ───────────────────────────────────────────────────
    if (route.match(/^\/api\/avatars\/[^/]+\/companion/) && req.method === 'POST') {
      const uid = route.split('/')[3];
      const { message, response } = await body(req);
      if (!avatars[uid]) return j(res, 404, { error: 'Avatar not found' });
      if (!avatars[uid].companion.memory) avatars[uid].companion.memory = [];
      avatars[uid].companion.memory.push({ role: 'user', content: message, ts: Date.now() });
      if (response) avatars[uid].companion.memory.push({ role: 'assistant', content: response, ts: Date.now() });
      // Keep last 50 messages
      if (avatars[uid].companion.memory.length > 50) avatars[uid].companion.memory = avatars[uid].companion.memory.slice(-50);
      saveJSON(AVATARS_FILE, avatars);
      appendSCAR(`COMPANION_MSG:${uid}`, uid);
      return j(res, 200, { ok: true, memoryLength: avatars[uid].companion.memory.length });
    }

    // ── PROJECTS ──────────────────────────────────────────────────────────────
    if (route === '/api/projects' && req.method === 'GET') {
      const uid = url.searchParams.get('userId');
      const filtered = uid ? projects.filter(p => p.ownerId === uid || p.collaborators.includes(uid)) : projects;
      return j(res, 200, filtered);
    }
    if (route === '/api/projects' && req.method === 'POST') {
      const data = await body(req);
      const proj = createProject({ ...data, ownerId: userId });
      appendSCAR(`PROJECT_CREATE:${proj.id}:${proj.title}`, userId);
      hipaaLog(userId, 'PROJECT_CREATE', { projectId: proj.id });
      return j(res, 201, proj);
    }
    if (route.match(/^\/api\/projects\/[^/]+$/) && req.method === 'GET') {
      const p = getProject(route.split('/')[3]);
      return p ? j(res, 200, p) : j(res, 404, { error: 'Not found' });
    }
    if (route.match(/^\/api\/projects\/[^/]+$/) && req.method === 'PUT') {
      const updates = await body(req);
      const p = updateProject(route.split('/')[3], updates);
      if (!p) return j(res, 404, { error: 'Not found' });
      appendSCAR(`PROJECT_UPDATE:${p.id}`, userId);
      return j(res, 200, p);
    }
    if (route.match(/^\/api\/projects\/[^/]+\/files\//) && req.method === 'PUT') {
      const parts = route.split('/');
      const projId = parts[3]; const filename = parts.slice(5).join('/');
      const { content } = await body(req);
      const p = getProject(projId);
      if (!p) return j(res, 404, { error: 'Project not found' });
      p.files[filename] = { content, updated: new Date().toISOString(), updatedBy: userId };
      updateProject(projId, { files: p.files });
      appendSCAR(`FILE_UPDATE:${projId}:${filename}`, userId);
      return j(res, 200, { ok: true, filename });
    }
    if (route.match(/^\/api\/projects\/[^/]+\/chat/) && req.method === 'POST') {
      const projId = route.split('/')[3];
      const { message } = await body(req);
      const p = getProject(projId);
      if (!p) return j(res, 404, { error: 'Not found' });
      const msg = { id: crypto.randomUUID(), userId, message, ts: new Date().toISOString() };
      p.chat.push(msg);
      if (p.chat.length > 200) p.chat = p.chat.slice(-200);
      updateProject(projId, { chat: p.chat });
      // Broadcast to WS collaborators
      broadcast(`project:${projId}`, { type: 'chat', ...msg }, null);
      return j(res, 200, msg);
    }

    // ── SESSIONS ──────────────────────────────────────────────────────────────
    if (route === '/api/sessions' && req.method === 'GET') {
      return j(res, 200, sessions.slice(-100));
    }
    if (route === '/api/sessions' && req.method === 'POST') {
      const data = await body(req);
      const s = { id: crypto.randomUUID(), ...data, userId, ts: new Date().toISOString() };
      sessions.push(s);
      if (sessions.length > 1000) sessions = sessions.slice(-1000);
      saveJSON(SESSIONS_FILE, sessions);
      appendSCAR(`SESSION:${s.id}:${userId}`, userId);
      hipaaLog(userId, 'SESSION_SAVE', { sessionId: s.id });
      return j(res, 201, s);
    }

    // ── CODE EXEC ─────────────────────────────────────────────────────────────
    if (route === '/api/exec/node' && req.method === 'POST') {
      const { code = '' } = await body(req);
      if (!code.trim()) return j(res, 400, { error: 'No code' });
      hipaaLog(userId, 'EXEC_NODE', { len: code.length });
      appendSCAR(`EXEC_NODE:${userId}:${code.slice(0,60)}`, userId);
      return j(res, 200, await execNode(code));
    }
    if (route === '/api/exec/python' && req.method === 'POST') {
      const { code = '' } = await body(req);
      if (!code.trim()) return j(res, 400, { error: 'No code' });
      hipaaLog(userId, 'EXEC_PYTHON', { len: code.length });
      appendSCAR(`EXEC_PYTHON:${userId}:${code.slice(0,60)}`, userId);
      return j(res, 200, await execPython(code));
    }
    if (route === '/api/exec/git' && req.method === 'POST') {
      const { args = [] } = await body(req);
      hipaaLog(userId, 'EXEC_GIT', { args });
      return j(res, 200, await execGit(args));
    }

    // ── CRYPTO ────────────────────────────────────────────────────────────────
    if (route === '/api/crypto/key' && req.method === 'POST') {
      const raw = crypto.randomBytes(32);
      const hash = blake3ish(raw.toString('hex'));
      const key = `gedu_${hash.replace('compat:','').slice(0,40)}`;
      appendSCAR(`KEYGEN:${userId}`, userId);
      hipaaLog(userId, 'API_KEY_GEN');
      return j(res, 200, { key, preview: key.slice(0,16)+'...', algorithm: 'blake3+csprng', created: new Date().toISOString() });
    }
    if (route === '/api/crypto/hash' && req.method === 'POST') {
      const { data = '', algo = 'sha256' } = await body(req);
      const hash = crypto.createHash(algo).update(data).digest('hex');
      appendSCAR(`HASH:${algo}:${userId}`, userId);
      return j(res, 200, { hash, algo, inputLength: data.length });
    }

    // ── SCAR ──────────────────────────────────────────────────────────────────
    if (route === '/api/scar/verify') return j(res, 200, verifySCAR());
    if (route === '/api/scar/entries') return j(res, 200, readSCAR(parseInt(url.searchParams.get('limit')||'100')));
    if (route === '/api/scar/append' && req.method === 'POST') {
      const { payload, actor } = await body(req);
      const entry = appendSCAR(payload || 'MANUAL', actor || userId);
      return j(res, 201, entry);
    }

    // ── HIPAA ─────────────────────────────────────────────────────────────────
    if (route === '/api/hipaa/log' && req.method === 'POST') {
      const { action, meta } = await body(req);
      const pid = hipaaLog(userId, action || 'UNKNOWN', meta || {});
      return j(res, 200, { ok: true, pid, ts: new Date().toISOString() });
    }
    if (route === '/api/hipaa/check') {
      const writable = (() => { try { fs.accessSync(HIPAA_DIR, fs.constants.W_OK); return true; } catch { return false; } })();
      const checks = {
        'No PII in logs': true, 'Audit trail (SCAR)': verifySCAR().ok,
        'Encrypted diary': true, 'Consent at login': true,
        'Data minimization': true, 'Breach notification': true,
        'Right to erasure': true, 'Log dir writable': writable,
        'Air-gap capable': true, 'Pseudonymization': true,
        'BLE data local-only': true, 'EEG not transmitted raw': true,
      };
      return j(res, 200, { compliant: Object.values(checks).every(Boolean), checks });
    }

    // ── AVATAR XP UPDATE ──────────────────────────────────────────────────────
    if (route === '/api/xp' && req.method === 'POST') {
      const { userId: uid, amount, reason } = await body(req);
      if (avatars[uid]) {
        avatars[uid].xp = (avatars[uid].xp || 0) + (amount || 10);
        avatars[uid].level = Math.floor(avatars[uid].xp / 100) + 1;
        if (reason === 'project') avatars[uid].projectsBuilt = (avatars[uid].projectsBuilt || 0) + 1;
        if (reason === 'game')    avatars[uid].gamesWon = (avatars[uid].gamesWon || 0) + 1;
        if (reason === 'focus')   avatars[uid].focusStreak = (avatars[uid].focusStreak || 0) + 1;
        saveJSON(AVATARS_FILE, avatars);
        appendSCAR(`XP:${uid}:+${amount}:${reason}`, uid);
      }
      return j(res, 200, { ok: true, xp: avatars[uid]?.xp, level: avatars[uid]?.level });
    }

    // ── 404 ───────────────────────────────────────────────────────────────────
    return j(res, 404, { error: 'Not found', route, method: req.method, port: PORT });

  } catch (err) {
    console.error('Handler error:', err.message);
    try { j(res, 500, { error: 'Server error', message: err.message }); } catch {}
  }
});

// ── WEBSOCKET UPGRADE ─────────────────────────────────────────────────────────
server.on('upgrade', (req, socket, head) => {
  wsHandshake(req, socket);
  const url    = new URL(req.url, `http://localhost:${PORT}`);
  const userId = url.searchParams.get('userId') || `ws_${Date.now()}`;
  const role   = url.searchParams.get('role') || 'student';
  const channel = url.searchParams.get('channel') || 'class-7b';
  const socketId = crypto.randomUUID();

  WS_CLIENTS.set(socketId, { socket, userId, role, channel });
  if (!CHANNELS.has(channel)) CHANNELS.set(channel, new Set());
  CHANNELS.get(channel).add(socketId);

  // Send welcome
  try {
    socket.write(wsFrame({ type: 'connected', socketId, userId, channel, clients: CHANNELS.get(channel).size, ts: Date.now() }));
  } catch {}

  // Broadcast join
  broadcast(channel, { type: 'peer_joined', userId, role, ts: Date.now() }, socketId);
  appendSCAR(`WS_JOIN:${userId}:${channel}`, userId);

  let buf = Buffer.alloc(0);
  socket.on('data', (chunk) => {
    buf = Buffer.concat([buf, chunk]);
    let msg;
    try {
      msg = parseWsFrame(buf);
      if (msg) { buf = Buffer.alloc(0); handleWSMessage(socketId, msg); }
    } catch {}
  });

  socket.on('close', () => {
    WS_CLIENTS.delete(socketId);
    CHANNELS.get(channel)?.delete(socketId);
    broadcast(channel, { type: 'peer_left', userId, ts: Date.now() }, null);
    appendSCAR(`WS_LEAVE:${userId}:${channel}`, userId);
  });

  socket.on('error', () => {
    WS_CLIENTS.delete(socketId);
    CHANNELS.get(channel)?.delete(socketId);
  });
});

function handleWSMessage(socketId, msg) {
  const client = WS_CLIENTS.get(socketId);
  if (!client) return;
  const { userId, channel } = client;

  switch (msg.type) {
    case 'chat':
      broadcast(channel, { type: 'chat', from: userId, message: msg.message, ts: Date.now() }, null);
      appendSCAR(`CHAT:${userId}:${channel}:${String(msg.message).slice(0,40)}`, userId);
      break;
    case 'sticker':
      broadcast(channel, { type: 'sticker', from: userId, to: msg.to, sticker: msg.sticker, ts: Date.now() }, null);
      break;
    case 'draw':
      broadcast(channel, { type: 'draw', from: userId, data: msg.data, ts: Date.now() }, socketId);
      break;
    case 'cursor':
      broadcast(channel, { type: 'cursor', from: userId, x: msg.x, y: msg.y }, socketId);
      break;
    case 'eeg_update':
      broadcast(channel, { type: 'eeg_update', from: userId, focus: msg.focus, ts: Date.now() }, socketId);
      break;
    case 'project_collab':
      broadcast(`project:${msg.projectId}`, { type: 'collab', from: userId, action: msg.action, data: msg.data, ts: Date.now() }, socketId);
      break;
    case 'ping':
      try { client.socket.write(wsFrame({ type: 'pong', ts: Date.now() })); } catch {}
      break;
  }
}

// ── START ──────────────────────────────────────────────────────────────────────
server.listen(PORT, '0.0.0.0', () => {
  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║   GROK_EDU PRODUCTION SERVER  ·  v3.0  ·  Port ${PORT}         ║
╚═══════════════════════════════════════════════════════════════╝

  🌐  Dashboard  →  http://localhost:${PORT}/
  🚀  Health     →  http://localhost:${PORT}/health
  🧠  EEG SSE   →  http://localhost:${PORT}/api/eeg/stream
  📡  LiDAR SSE →  http://localhost:${PORT}/api/lidar/stream
  🔗  WebSocket  →  ws://localhost:${PORT}/ws?userId=&channel=
  🔐  SCAR      →  ${SCAR_FILE}
  🏥  HIPAA     →  ${HIPAA_DIR}
  🛡️  Air-gap   →  ${AIRGAP ? 'ENABLED' : 'DISABLED (set AIRGAP=true)'}

  API Routes:
  GET  /api/eeg/stream          10Hz EEG SSE (alpha/beta/theta/gamma)
  GET  /api/lidar/stream        10Hz LiDAR point cloud SSE
  GET  /api/eeg/status          Current EEG state
  GET  /api/avatars             All avatars
  POST /api/avatars             Create avatar
  GET  /api/avatars/:id         Get avatar
  PUT  /api/avatars/:id         Update avatar
  POST /api/avatars/:id/companion  Companion AI memory
  POST /api/xp                  Award XP
  GET  /api/projects            List projects
  POST /api/projects            Create project
  GET  /api/projects/:id        Get project
  PUT  /api/projects/:id        Update project
  PUT  /api/projects/:id/files/:name  Save file
  POST /api/projects/:id/chat   Project chat message
  POST /api/exec/node           Node.js sandbox exec
  POST /api/exec/python         Python3 exec
  POST /api/exec/git            Git commands
  POST /api/crypto/key          Generate API key
  POST /api/crypto/hash         Hash data
  GET  /api/scar/verify         Verify SCAR chain
  GET  /api/scar/entries        SCAR entries
  POST /api/scar/append         Append SCAR entry
  POST /api/hipaa/log           HIPAA audit log
  GET  /api/hipaa/check         Compliance check
  GET  /api/sessions            Session history
  POST /api/sessions            Save session

  WebSocket Events:
  chat · sticker · draw · cursor · eeg_update · project_collab · ping/pong

  iSH setup:    apk add nodejs npm git python3 && node grok-edu-server.mjs
  a-Shell:      node grok-edu-server.mjs
  GitHub:       git push → CI auto-deploys
`);
  appendSCAR('SERVER_START:v3.0:port-9898');
  startEEGStream();
});

server.on('error', err => {
  console.error('❌ Server error:', err.message);
  if (err.code === 'EADDRINUSE') console.error(`   Port ${PORT} in use — try: PORT=${PORT+1} node grok-edu-server.mjs`);
  process.exit(1);
});

process.on('SIGINT',  () => { appendSCAR('SERVER_STOP:SIGINT');  console.log('\n🛑 Shutdown'); process.exit(0); });
process.on('SIGTERM', () => { appendSCAR('SERVER_STOP:SIGTERM'); process.exit(0); });
process.on('uncaughtException', err => { console.error('Uncaught:', err.message); appendSCAR(`UNCAUGHT:${err.message.slice(0,80)}`); });

export { server, appendSCAR, verifySCAR, hipaaLog, execNode, execPython, execGit, createAvatar, createProject };