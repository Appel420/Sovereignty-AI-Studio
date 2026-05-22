// === MASTER KEY LOADING (STABILIZED + MEMORY SAFE) ===
let MASTER_KEY;
const KEY_FILE = process.env.KEY_FILE || path.join(__dirname, '.master.key');
const _keyB64 = process.env.MASTER_KEY_B64 || '';

if (_keyB64.length >= 86) {
  MASTER_KEY = Buffer.from(_keyB64, 'base64');
  if (MASTER_KEY.length !== 64) {
    process.stderr.write('[FATAL] MASTER_KEY_B64 decoded to invalid length (need 64 bytes).\n');
    process.exit(1);
  }
  if (process.env.VERBOSE) {
    process.stderr.write('[KEY] Loaded MASTER_KEY from MASTER_KEY_B64 env var\n');
  }
} else if (fs.existsSync(KEY_FILE)) {
  try {
    MASTER_KEY = fs.readFileSync(KEY_FILE);
    if (MASTER_KEY.length !== 64) {
      process.stderr.write('[FATAL] Existing key file has invalid length. Run: npm run keygen\n');
      process.exit(1);
    }
    if (process.env.VERBOSE) {
      process.stderr.write('[KEY] Loaded existing MASTER_KEY from ' + KEY_FILE + '\n');
    }
  } catch (e) {
    process.stderr.write('[FATAL] Failed to read key file: ' + e.message + '\n');
    process.exit(1);
  }
} else {
  // Only generate a new key on true first initialization
  MASTER_KEY = crypto.randomBytes(64);
  fs.writeFileSync(KEY_FILE, MASTER_KEY, { mode: 0o600 });
  process.stderr.write('[KEY] Generated new master key → ' + KEY_FILE + '\n');
  process.stderr.write('[KEY] Set MASTER_KEY_B64 in .env to persist across restarts (npm run keygen)\n');
}

// === CRITICAL: Memory + Hydration must initialize HERE ===
// Right after we have a stable MASTER_KEY, before any session or rotation logic.
// await initMemoryAndHydration(MASTER_KEY);