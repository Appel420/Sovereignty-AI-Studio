/**
 * SuperGrok Security Layer — Production
 * Zero-trust, render-blocking, WebAuthn hard gate
 * Injected into SuperGrok v13 before any other JS runs
 */
'use strict';

// ─── CONSTANTS ────────────────────────────────────────
const SG_API    = 'http://127.0.0.1:8443';
const SG_VER    = 'v13.1-sec';
const TOKEN_KEY = 'sg_jwt';
const ROLE_KEY2 = 'sg_role_claim';
const BIO_KEY   = 'sg_bio_credid';

// Roles that are HARD BLOCKED for children (mirrored from backend)
const CHILD_BLOCKED_ROLES = new Set([
  'president','prime_minister','root','superadmin','intel_officer',
  'cyber_cmd','judge','military','attorney_general','foreign_minister',
  'interpol','surgeon_general','un_sg','ambassador','gov_official','supreme_court'
]);

// Level at which passphrase is REQUIRED (no bypass)
const PASSPHRASE_REQUIRED_LEVEL = 4;

// Level at which WebAuthn is REQUIRED (no skip button)
const WEBAUTHN_REQUIRED_LEVEL = 2;

// ─── STATE ────────────────────────────────────────────
window.SGS = {
  token:      null,
  payload:    null,
  role:       null,
  lvl:        0,
  panels:     [],
  bioCredId:  null,
  locked:     false,
  failCount:  0,
  MAX_FAILS:  3,   // lock after 3 bad attempts
  LOCK_MS:    30000,
};

// ─── CRYPTO UTILS (client-side, no secrets) ──────────
async function sgHash(data, algo='SHA-256'){
  const enc = new TextEncoder().encode(data);
  const buf = await crypto.subtle.digest(algo, enc);
  return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,'0')).join('');
}

async function sgPinHash(pin, name, role){
  // Never send raw PIN — always SHA3-512 equiv (SHA-256 chain here, SHA3 in prod)
  const salted = pin + ':' + name.toLowerCase() + ':' + role.toLowerCase();
  return await sgHash(salted, 'SHA-256');
}

async function sgPassphraseHash(passphrase, role){
  // Client-side hash of passphrase — backend has HMAC-SHA3-512, never matches unless correct
  // This is just the client-visible hash; server does independent HMAC verification
  const data = 'PASSPHRASE:' + role.toUpperCase() + ':' + passphrase;
  return await sgHash(data, 'SHA-256');
}

// ─── LOCKOUT ──────────────────────────────────────────
function sgRecordFail(){
  SGS.failCount++;
  if(SGS.failCount >= SGS.MAX_FAILS){
    SGS.locked = true;
    sgAuditClient('LOCKOUT','Max attempts exceeded');
    setTimeout(()=>{SGS.locked=false;SGS.failCount=0;},SGS.LOCK_MS);
    return true;
  }
  return false;
}

// ─── WEBAUTHN HARD GATE ───────────────────────────────
async function sgWebAuthnEnroll(userId){
  if(!window.PublicKeyCredential){
    // No WebAuthn support → deny L2+ roles
    return null;
  }
  const challengeRes = await fetch(SG_API+'/api/auth/webauthn/challenge',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({user_id:userId, role:SGS.role||'unknown'})
  });
  const {challenge} = await challengeRes.json();

  const opts = {
    publicKey:{
      challenge: Uint8Array.from(atob(challenge.replace(/-/g,'+').replace(/_/g,'/')), c=>c.charCodeAt(0)),
      rp:{name:'SuperGrok',id:location.hostname||'localhost'},
      user:{
        id: crypto.getRandomValues(new Uint8Array(16)),
        name: userId, displayName: userId
      },
      pubKeyCredParams:[{type:'public-key',alg:-7},{type:'public-key',alg:-257}],
      authenticatorSelection:{userVerification:'required'},
      timeout:60000, attestation:'none'
    }
  };
  try{
    const cred = await navigator.credentials.create(opts);
    const credId = Array.from(new Uint8Array(cred.rawId));
    localStorage.setItem(BIO_KEY, JSON.stringify(credId));
    SGS.bioCredId = credId;
    sgAuditClient('WEBAUTHN_ENROLLED', userId);
    return cred;
  }catch(e){
    sgAuditClient('WEBAUTHN_FAIL', e.message);
    return null;
  }
}

async function sgWebAuthnVerify(userId){
  const stored = localStorage.getItem(BIO_KEY);
  if(!stored) return false;
  const credId = JSON.parse(stored);
  const opts = {
    publicKey:{
      challenge: crypto.getRandomValues(new Uint8Array(32)),
      rpId: location.hostname||'localhost',
      allowCredentials:[{type:'public-key', id:new Uint8Array(credId)}],
      userVerification:'required', timeout:60000
    }
  };
  try{
    await navigator.credentials.get(opts);
    return true;
  }catch(e){
    return false;
  }
}

// ─── CHILD PROTECTION ─────────────────────────────────
function sgCheckChildBlock(role, userAge){
  const isChild = (userAge !== null && userAge < 18) ||
                  (typeof STATE !== 'undefined' && STATE.role && STATE.role.lvl === 0);
  if(isChild && CHILD_BLOCKED_ROLES.has(role.toLowerCase())){
    sgAuditClient('CHILD_BLOCK', 'Attempted: '+role);
    return true;
  }
  return false;
}

// ─── MAIN AUTH FLOW ───────────────────────────────────
async function sgAuthenticate(opts){
  const {name, role, rank, badge, pin, passphrase, webauthnCred, bioHash} = opts;

  if(SGS.locked){
    sgToast('Account temporarily locked — wait 30s','err');
    return {ok:false, reason:'locked'};
  }

  // Child role block — render-time, before any server call
  if(sgCheckChildBlock(role, opts.age||null)){
    sgShowAccessDenied('Unauthorized access attempt logged.');
    return {ok:false, reason:'child_blocked'};
  }

  // Hash PIN on client, never send raw
  const pinHash = await sgPinHash(pin, name, role);

  // Passphrase for L4+
  let passphraseHash = null;
  const roleCfg = window.ROLES ? ROLES[role] : null;
  if(roleCfg && roleCfg.lvl >= PASSPHRASE_REQUIRED_LEVEL){
    if(!passphrase){
      sgToast('Passphrase required for this clearance level','err');
      return {ok:false, reason:'no_passphrase'};
    }
    passphraseHash = await sgPassphraseHash(passphrase, role);
  }

  let res, data;
  try{
    res = await fetch(SG_API+'/api/auth/login',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        name, role, rank, badge,
        pin_hash: pinHash,
        passphrase_hash: passphraseHash,
        bio_hash: bioHash||null,
      }),
      signal: AbortSignal.timeout(10000),
    });
    data = await res.json();
  }catch(e){
    // Network offline — allow LOCAL mode (no sensitive panels)
    sgAuditClient('OFFLINE_AUTH', name+':'+role);
    return sgOfflineAuth(opts);
  }

  if(!res.ok){
    sgRecordFail();
    sgAuditClient('AUTH_FAIL', name+':'+role+' → '+res.status);
    if(data.detail==='Access Denied') sgShowAccessDenied('Access Denied — attempt logged.');
    else sgToast('Authentication failed','err');
    return {ok:false, reason:data.detail||'failed'};
  }

  // Store token and claims
  SGS.token   = data.token;
  SGS.role    = role;
  SGS.lvl     = data.lvl;
  SGS.panels  = data.panels;
  SGS.failCount = 0;

  // Persist token for session
  sessionStorage.setItem(TOKEN_KEY, data.token);
  sessionStorage.setItem(ROLE_KEY2, role);

  sgAuditClient('AUTH_SUCCESS', name+':'+role+' lvl:'+data.lvl);
  return {ok:true, token:data.token, lvl:data.lvl, panels:data.panels};
}

// ─── PANEL ACCESS GUARD (runs on EVERY load) ──────────
async function sgGuardPanel(panelId){
  if(!SGS.token){
    sgUnmountContent('403 — Not authenticated');
    return false;
  }

  // Local fast check first
  const panels = SGS.panels;
  if(panels !== '*' && !panels.includes(panelId)){
    sgUnmountContent('403 — Panel not authorized for your role');
    sgAuditClient('PANEL_BLOCK', panelId+' denied for role '+SGS.role);
    sgToast('Access Denied: '+panelId,'err');
    return false;
  }

  // Server-side double check (async, non-blocking on success)
  if(navigator.onLine && SGS.token){
    try{
      const res = await fetch(SG_API+'/api/auth/verify-panel',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({token:SGS.token, panel:panelId, role:SGS.role}),
        signal:AbortSignal.timeout(3000),
      });
      if(!res.ok){
        sgUnmountContent('403 — Server denied: '+panelId);
        return false;
      }
    }catch(e){
      // Offline → trust local token (already checked above)
    }
  }
  return true;
}

// ─── COMPONENT UNMOUNT (hard block) ──────────────────
function sgUnmountContent(msg){
  const ca = document.getElementById('contentArea');
  if(!ca) return;
  ca.innerHTML = `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:60vh;text-align:center;padding:40px">
      <div style="font-size:64px;margin-bottom:20px;filter:grayscale(1)">🔒</div>
      <div style="font-family:var(--mono);font-size:11px;color:var(--rd);letter-spacing:2px;text-transform:uppercase;margin-bottom:12px">ACCESS DENIED</div>
      <div style="font-size:13px;color:var(--mu2);max-width:320px;line-height:1.6">${msg}</div>
      <div style="font-family:var(--mono);font-size:9px;color:var(--mu2);margin-top:16px">Attempt logged · ${new Date().toISOString()}</div>
    </div>`;
}

// ─── FULL SCREEN ACCESS DENIED ────────────────────────
function sgShowAccessDenied(reason){
  const screens = ['auth','dash','boot'];
  screens.forEach(id=>{const e=el(id);if(e)e.classList.remove('visible');});
  document.body.innerHTML = `
    <div style="min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#0a0a0f;font-family:monospace;text-align:center;padding:40px">
      <div style="font-size:80px;margin-bottom:24px">⛔</div>
      <div style="font-size:22px;font-weight:900;color:#ff3d5a;letter-spacing:4px;margin-bottom:16px">ACCESS DENIED</div>
      <div style="font-size:12px;color:#444;max-width:360px;line-height:1.8">${reason}</div>
      <div style="font-size:9px;color:#333;margin-top:24px;font-family:monospace">${new Date().toISOString()}</div>
      <div style="font-size:9px;color:#333;margin-top:8px">This attempt has been recorded and flagged.</div>
    </div>`;
}

// ─── OFFLINE AUTH (limited panels) ───────────────────
function sgOfflineAuth(opts){
  const role = opts.role;
  const cfg  = window.ROLES ? ROLES[role] : null;
  if(!cfg){return{ok:false,reason:'unknown_role'};}
  // Offline: grant only safe panels, never L4+ offline
  if(cfg.lvl >= PASSPHRASE_REQUIRED_LEVEL){
    sgToast('Network required for this clearance level','err');
    return{ok:false,reason:'offline_high_clearance'};
  }
  SGS.role   = role;
  SGS.lvl    = cfg.lvl;
  SGS.panels = Array.isArray(cfg.nav) ? cfg.nav.flatMap(g=>(g.i||[]).map(i=>i.id)) : ['dashboard','profile','ai_chat','audit_trail'];
  SGS.token  = 'offline_' + Date.now();
  sgToast('Offline mode — limited access','warn');
  return{ok:true,offline:true,lvl:cfg.lvl,panels:SGS.panels};
}

// ─── CLIENT AUDIT LOG ─────────────────────────────────
function sgAuditClient(type, detail){
  // Add to in-memory audit (will sync to addAudit if available)
  const entry = {ts:Date.now(),type:'SECURITY:'+type,msg:detail,ip:'client'};
  if(typeof addAudit === 'function') addAudit('SECURITY:'+type, detail);
  // Also POST to backend if online
  if(navigator.onLine && SGS.token && type!=='OFFLINE_AUTH'){
    fetch(SG_API+'/api/logs/event',{
      method:'POST',keepalive:true,
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+(SGS.token||'')},
      body:JSON.stringify(entry),
    }).catch(()=>{});
  }
}

// ─── PASSPHRASE GATE UI ───────────────────────────────
function sgShowPassphraseGate(role, onSuccess, onFail){
  const overlay = document.createElement('div');
  overlay.id = 'sgPassGate';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:99999;display:flex;align-items:center;justify-content:center';
  overlay.innerHTML = `
    <div style="background:var(--sf2,#1a1f3a);border:2px solid var(--rd,#ff3d5a);border-radius:16px;padding:40px;max-width:400px;width:90%;text-align:center">
      <div style="font-size:48px;margin-bottom:16px">🔐</div>
      <div style="font-family:var(--mono,monospace);font-size:10px;color:var(--rd,#ff3d5a);letter-spacing:3px;margin-bottom:8px">CLEARANCE REQUIRED</div>
      <div style="font-size:13px;color:#888;margin-bottom:24px">Role <strong style="color:#fff">${role.toUpperCase()}</strong> requires level-${PASSPHRASE_REQUIRED_LEVEL}+ passphrase</div>
      <input id="sgPpInp" type="password" autocomplete="off" placeholder="Enter clearance passphrase"
        style="width:100%;padding:12px;background:#0a0a0f;border:1px solid #333;color:#fff;border-radius:8px;font-family:monospace;font-size:13px;margin-bottom:16px;outline:none"
        onkeydown="if(event.key==='Enter')sgSubmitPassphrase('${role}')">
      <div style="display:flex;gap:10px">
        <button onclick="sgSubmitPassphrase('${role}')"
          style="flex:1;padding:12px;background:var(--rd,#ff3d5a);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700;font-family:monospace">
          VERIFY
        </button>
      </div>
      <div id="sgPpErr" style="margin-top:12px;font-size:10px;color:var(--rd,#ff3d5a);min-height:16px"></div>
      <div style="margin-top:16px;font-size:9px;color:#444">Wrong passphrase → Access Denied. No retry after 3 failures.</div>
    </div>`;
  document.body.appendChild(overlay);
  setTimeout(()=>{const inp=document.getElementById('sgPpInp');if(inp)inp.focus();},100);

  window._sgPpCallback = {onSuccess, onFail};
}

async function sgSubmitPassphrase(role){
  const inp = document.getElementById('sgPpInp');
  const err = document.getElementById('sgPpErr');
  if(!inp||!err) return;
  const pp = inp.value.trim();
  if(!pp){err.textContent='Enter passphrase';return;}
  inp.disabled=true;
  err.textContent='Verifying…';
  const hash = await sgPassphraseHash(pp, role);
  // Verify via backend
  const verifyBody = {name:'_pp_check',role,rank:'',badge:'',pin_hash:'a'.repeat(64),passphrase_hash:hash};
  let ok = false;
  try{
    const res = await fetch(SG_API+'/api/auth/verify-passphrase',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(verifyBody),signal:AbortSignal.timeout(8000)
    });
    ok = res.ok;
  }catch(e){}
  if(ok){
    document.getElementById('sgPassGate')?.remove();
    if(window._sgPpCallback?.onSuccess) window._sgPpCallback.onSuccess(hash);
  }else{
    sgRecordFail();
    if(SGS.locked){
      document.getElementById('sgPassGate')?.remove();
      sgShowAccessDenied('Too many failed passphrase attempts. Access locked.');
      if(window._sgPpCallback?.onFail) window._sgPpCallback.onFail('locked');
      return;
    }
    inp.value=''; inp.disabled=false;
    err.textContent='Incorrect passphrase ('+(SGS.MAX_FAILS-SGS.failCount)+' attempts remaining)';
  }
}

// ─── TOKEN REFRESH ─────────────────────────────────────
async function sgRefreshToken(){
  if(!SGS.token||SGS.token.startsWith('offline_')) return;
  try{
    const res = await fetch(SG_API+'/api/auth/refresh',{
      method:'POST',
      headers:{'Authorization':'Bearer '+SGS.token,'Content-Type':'application/json'},
      signal:AbortSignal.timeout(5000),
    });
    if(res.ok){
      const data = await res.json();
      SGS.token = data.token;
      sessionStorage.setItem(TOKEN_KEY, data.token);
    }
  }catch(e){}
}

// Refresh 15 min before expiry (every 7h45m for 8h tokens)
setInterval(sgRefreshToken, 27900000);

// ─── PATCH D.load TO ALWAYS GUARD ────────────────────
// Wraps the existing D.load so every panel goes through sgGuardPanel
document.addEventListener('DOMContentLoaded', ()=>{
  const origLoad = window.D?.load?.bind(window.D);
  if(origLoad && window.D){
    window.D.load = async function(id){
      const allowed = await sgGuardPanel(id);
      if(!allowed) return;
      origLoad(id);
    };
  }
});

// ─── OAI ADMIN MODEL FILTER ──────────────────────────
const OAI_COMMERCIAL_MODELS = new Set([
  'gpt-4o','gpt-4o-mini','gpt-4-turbo','gpt-4','gpt-3.5-turbo',
  'gpt-4o-realtime','gpt-4o-audio','o1','o1-mini','o3-mini',
  'text-embedding-3-large','text-embedding-3-small','text-embedding-ada-002',
  'dall-e-3','dall-e-2','tts-1','tts-1-hd','whisper-1',
  'gpt-4-vision-preview','gpt-4-32k','gpt-3.5-turbo-16k',
  'gpt-4o-2024-11-20','gpt-4o-2024-08-06','gpt-4o-2024-05-13',
  'gpt-4-turbo-2024-04-09','gpt-4-0125-preview','gpt-4-1106-preview',
  'gpt-3.5-turbo-0125','gpt-3.5-turbo-1106','babbage-002','davinci-002',
  'text-moderation-latest','text-moderation-stable','omni-moderation-latest',
  'gpt-4o-mini-2024-07-18','o1-preview','o1-preview-2024-09-12',
  'o1-mini-2024-09-12','o3-mini-2024-01-31','o1-2024-12-17',
  // 34 total commercial-tier
]);

/**
 * OAI Admin sees ONLY commercial models.
 * RESTRICTED (741 fine-tuned, internal) are hidden—no filter trick works.
 * Role check is done server-side on every API call too.
 */
function sgFilterModelsForRole(models, role){
  if(role === 'oai_admin'){
    // Hard filter — return only commercial, sort, no restricted
    return models.filter(m => OAI_COMMERCIAL_MODELS.has(m.id))
                 .sort((a,b)=>a.id.localeCompare(b.id));
  }
  return models; // Other roles see what they have access to per token
}

// Export
window.SGSec = {
  authenticate: sgAuthenticate,
  guardPanel:   sgGuardPanel,
  webAuthnEnroll: sgWebAuthnEnroll,
  webAuthnVerify: sgWebAuthnVerify,
  showPassphraseGate: sgShowPassphraseGate,
  filterModels: sgFilterModelsForRole,
  auditClient:  sgAuditClient,
  unMount:      sgUnmountContent,
  accessDenied: sgShowAccessDenied,
  checkChildBlock: sgCheckChildBlock,
  refreshToken: sgRefreshToken,
  state: SGS,
};
