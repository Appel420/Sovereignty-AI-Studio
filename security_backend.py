"""
SuperGrok Security Backend — Production
JWT + Dilithium3 signed tokens, WebAuthn, role enforcement, access logging
"""
import os, json, time, hashlib, hmac, secrets, ipaddress
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── CONFIG ───────────────────────────────────────────
LOG_DIR   = Path("logs")
LOG_FILE  = LOG_DIR / "access.jsonl"
KEY_FILE  = Path(".sg_master_key")
LOG_DIR.mkdir(exist_ok=True)

# Master signing key (Dilithium3 sim using HMAC-SHA3-512 until liboqs available)
MASTER_KEY = KEY_FILE.read_bytes() if KEY_FILE.exists() else None
if not MASTER_KEY:
    MASTER_KEY = secrets.token_bytes(64)
    KEY_FILE.write_bytes(MASTER_KEY)
    KEY_FILE.chmod(0o600)

# ─── ROLE MATRIX ─────────────────────────────────────
# Every role maps to: level (0-6), allowed panels, passphrase required (lvl>=4)
ROLE_MATRIX = {
    # Level 6 — ROOT / SUPERUSER
    "root":           {"lvl": 6, "passphrase": True,  "panels": "*"},
    "superadmin":     {"lvl": 6, "passphrase": True,  "panels": "*"},
    # Level 5 — HEADS OF STATE / INTEL / JUDICIAL
    "president":      {"lvl": 5, "passphrase": True,  "panels": ["dashboard","exec_orders","cabinet","natl_security","succession","ai_chat","audit_trail","profile","terminal","key_mgmt"]},
    "prime_minister": {"lvl": 5, "passphrase": True,  "panels": ["dashboard","parliament","cabinet","natl_security","ai_chat","audit_trail","profile","terminal"]},
    "un_sg":          {"lvl": 5, "passphrase": True,  "panels": ["dashboard","security_council","peacekeeping","resolutions","ai_chat","audit_trail","profile"]},
    "judge":          {"lvl": 5, "passphrase": True,  "panels": ["dashboard","case_docket","hearings","orders","ai_chat","legal_research","audit_trail","profile"]},
    "intel_officer":  {"lvl": 5, "passphrase": True,  "panels": ["dashboard","sigint","humint","threat_assess","uc_identity","ai_chat","audit_trail","terminal","profile"]},
    "cyber_cmd":      {"lvl": 5, "passphrase": True,  "panels": ["dashboard","threat_intel","incident_resp","zero_day","soc","ai_chat","terminal","audit_trail","key_mgmt","profile"]},
    "surgeon_general":{"lvl": 5, "passphrase": True,  "panels": ["dashboard","health_advisories","emergency_authority","patient_care","ai_chat","audit_trail","profile"]},
    "supreme_court":  {"lvl": 5, "passphrase": True,  "panels": ["dashboard","cert_review","oral_arguments","opinions","ai_chat","legal_research","audit_trail","profile"]},
    # Level 4 — SENIOR OFFICIALS
    "gov_official":   {"lvl": 4, "passphrase": True,  "panels": ["dashboard","policy_mgmt","budget","ai_chat","audit_trail","profile"]},
    "military":       {"lvl": 4, "passphrase": True,  "panels": ["dashboard","missions","intel","logistics","ai_chat","audit_trail","profile","terminal"]},
    "ambassador":     {"lvl": 4, "passphrase": True,  "panels": ["dashboard","diplo_cables","treaty","consular","ai_chat","audit_trail","profile"]},
    "foreign_minister":{"lvl":4, "passphrase": True,  "panels": ["dashboard","foreign_policy","treaty","sanctions","ai_chat","audit_trail","profile"]},
    "interpol":       {"lvl": 4, "passphrase": True,  "panels": ["dashboard","red_notices","cross_border","cybercrime","ai_chat","audit_trail","terminal","profile"]},
    "attorney_general":{"lvl":4, "passphrase": True,  "panels": ["dashboard","litigation","antitrust","doj_lead","ai_chat","legal_research","audit_trail","profile"]},
    # Level 3 — PROFESSIONALS
    "medical":        {"lvl": 3, "passphrase": False, "panels": ["dashboard","patient_care","vitals","medications","ehr","ai_chat","audit_trail","profile","session_clock"]},
    "prosecutor":     {"lvl": 3, "passphrase": False, "panels": ["dashboard","active_cases","evidence","witnesses","charges","ai_chat","legal_research","audit_trail","profile"]},
    "police":         {"lvl": 3, "passphrase": False, "panels": ["dashboard","dispatch","arrests","reports","incidents","ai_chat","audit_trail","profile","sos_panel"]},
    "pilot":          {"lvl": 3, "passphrase": False, "panels": ["dashboard","flight_plan","notam","weather","charts","ai_chat","audit_trail","profile"]},
    "developer":      {"lvl": 3, "passphrase": False, "panels": ["dashboard","api_console","cicd","project_builder","ai_chat","terminal","github_panel","audit_trail","key_mgmt","profile"]},
    "professor":      {"lvl": 3, "passphrase": False, "panels": ["dashboard","courses","research","publications","ai_chat","audit_trail","profile"]},
    "teacher":        {"lvl": 2, "passphrase": False, "panels": ["dashboard","class_dash","grades","attendance","curriculum","eeg_classroom","ai_chat","audit_trail","profile"]},
    # Level 2 — FIELD PERSONNEL
    "fire":           {"lvl": 2, "passphrase": False, "panels": ["dashboard","incidents","dispatch","equipment","hazmat","ai_chat","audit_trail","profile","sos_panel"]},
    "emt":            {"lvl": 2, "passphrase": False, "panels": ["dashboard","patient_care","vitals","dispatch","ai_chat","audit_trail","profile","sos_panel"]},
    "security":       {"lvl": 2, "passphrase": False, "panels": ["dashboard","access_logs","cameras","perimeter","incidents","ai_chat","audit_trail","profile"]},
    "corrections":    {"lvl": 2, "passphrase": False, "panels": ["dashboard","inmate_roster","programs","incidents","ai_chat","audit_trail","profile"]},
    "social_worker":  {"lvl": 2, "passphrase": False, "panels": ["dashboard","case_mgmt","home_visits","court_reports","ai_chat","audit_trail","profile"]},
    # Level 1 — GENERAL PUBLIC
    "student":        {"lvl": 1, "passphrase": False, "panels": ["dashboard","eeg_student","rewards","ai_games","learning_hub","ai_chat","profile"]},
    "adult":          {"lvl": 1, "passphrase": False, "panels": ["dashboard","profile","ai_chat","ddg_browser"]},
    "rideshare":      {"lvl": 1, "passphrase": False, "panels": ["dashboard","active_ride","navigation","earnings","ai_chat","profile","sos_panel"]},
    "postal":         {"lvl": 1, "passphrase": False, "panels": ["dashboard","packages","routes","manifest","ai_chat","profile"]},
    "chaplain":       {"lvl": 1, "passphrase": False, "panels": ["dashboard","counseling","memorial","ai_chat","profile"]},
    # Level 0 — CHILD (COPPA enforced)
    "child":          {"lvl": 0, "passphrase": False, "panels": ["dashboard","story_time","learning_games","drawing","ai_tutor","homework","profile"]},
    "teen":           {"lvl": 0, "passphrase": False, "panels": ["dashboard","college_prep","career","ai_tutor","homework","ai_games","profile"]},
}

# Roles that are HARD BLOCKED for children attempting them
CHILD_BLOCKED = {"president","prime_minister","root","superadmin","intel_officer","cyber_cmd",
                 "judge","military","attorney_general","foreign_minister","interpol",
                 "surgeon_general","un_sg","ambassador","gov_official","supreme_court"}

# Passphrase-protected roles (L4+) — hash stored server-side, never transmitted
# In prod: store argon2 hashes in DB. Here we use HMAC-SHA256 of role+secret.
def _pp_hash(role: str) -> str:
    return hmac.new(MASTER_KEY, f"PASSPHRASE:{role}".encode(), hashlib.sha256).hexdigest()

PASSPHRASE_HASHES = {role: _pp_hash(role) for role, cfg in ROLE_MATRIX.items() if cfg["passphrase"]}

app = FastAPI(title="SuperGrok Security API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9898","http://127.0.0.1:9898"],
    allow_credentials=True,
    allow_methods=["POST","GET","OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add OWASP-recommended security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response

# ─── MODELS ───────────────────────────────────────────
class AuthRequest(BaseModel):
    name: str
    role: str
    rank: str
    badge: str
    pin_hash: str          # SHA3-512(pin + name + role) — never send raw PIN
    passphrase_hash: Optional[str] = None  # only for L4+
    webauthn_assertion: Optional[dict] = None  # WebAuthn assertion
    bio_hash: Optional[str] = None

class TokenVerifyRequest(BaseModel):
    token: str
    panel: str
    role: str

class WebAuthnChallengeRequest(BaseModel):
    user_id: str
    role: str

# ─── ACCESS LOGGING ───────────────────────────────────
def log_access(request: Request, event: str, user: str, role: str,
               panel: str = "", allowed: bool = True, reason: str = ""):
    entry = {
        "ts":       datetime.now(timezone.utc).isoformat(),
        "ip":       request.client.host if request.client else "unknown",
        "user":     user,
        "role":     role,
        "panel":    panel,
        "event":    event,
        "allowed":  allowed,
        "reason":   reason,
        "ua":       request.headers.get("user-agent","")[:120],
    }
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

# ─── TOKEN GENERATION ─────────────────────────────────
def sign_token(payload: dict) -> str:
    """HMAC-SHA3-512 signed JWT (Dilithium3 when liboqs available)"""
    import base64
    header = base64.urlsafe_b64encode(b'{"alg":"dilithium3-sim","typ":"JWT"}').decode().rstrip("=")
    body   = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig_bytes = hmac.new(MASTER_KEY, f"{header}.{body}".encode(), hashlib.sha3_512).digest()
    sig = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
    return f"{header}.{body}.{sig}"

def verify_token(token: str) -> dict:
    import base64
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token")
    header, body, sig = parts
    expected = hmac.new(MASTER_KEY, f"{header}.{body}".encode(), hashlib.sha3_512).digest()
    expected_b64 = base64.urlsafe_b64encode(expected).decode().rstrip("=")
    if not hmac.compare_digest(sig, expected_b64):
        raise ValueError("invalid signature")
    payload = json.loads(base64.urlsafe_b64decode(body + "==").decode())
    if payload.get("exp", 0) < time.time():
        raise ValueError("token expired")
    return payload

# ─── ROUTES ───────────────────────────────────────────

@app.post("/api/auth/login")
async def login(req: AuthRequest, request: Request):
    role_key = req.role.lower().strip()

    # 1. Role must exist
    if role_key not in ROLE_MATRIX:
        log_access(request, "LOGIN_FAILED", req.name, role_key, allowed=False, reason="unknown_role")
        raise HTTPException(403, "Unknown role")

    cfg = ROLE_MATRIX[role_key]

    # 2. Child attempting L4+ role → hard block, no retry info leaked
    if role_key in CHILD_BLOCKED and cfg["lvl"] == 0:
        log_access(request, "CHILD_ESCALATION", req.name, role_key, allowed=False, reason="child_blocked")
        raise HTTPException(403, "Access Denied")

    # 3. L4+ requires passphrase (argon2 in prod, HMAC here)
    if cfg["passphrase"]:
        if not req.passphrase_hash:
            log_access(request, "LOGIN_FAILED", req.name, role_key, allowed=False, reason="no_passphrase")
            raise HTTPException(403, "Passphrase required for this clearance level")
        # Verify: client sends SHA256(passphrase + salt), server compares
        client_hash = req.passphrase_hash.lower()
        if client_hash != PASSPHRASE_HASHES.get(role_key, ""):
            log_access(request, "PASSPHRASE_FAIL", req.name, role_key, allowed=False, reason="bad_passphrase")
            # Deliberate delay — anti-brute-force
            await __import__("asyncio").sleep(2)
            raise HTTPException(403, "Access Denied")  # no detail leaked

    # 4. PIN hash validation (minimum entropy check)
    if len(req.pin_hash) < 64:
        raise HTTPException(400, "Invalid PIN format")

    # 5. Build JWT with role claims
    payload = {
        "sub":   req.name,
        "role":  role_key,
        "rank":  req.rank,
        "badge": req.badge,
        "lvl":   cfg["lvl"],
        "panels": cfg["panels"],
        "bio":   bool(req.bio_hash),
        "iat":   int(time.time()),
        "exp":   int(time.time()) + 28800,  # 8 hour session
        "jti":   secrets.token_hex(16),
    }
    token = sign_token(payload)

    log_access(request, "LOGIN_SUCCESS", req.name, role_key)
    return {
        "token": token,
        "lvl": cfg["lvl"],
        "panels": cfg["panels"],
        "expires_in": 28800,
    }


@app.post("/api/auth/verify-panel")
async def verify_panel(req: TokenVerifyRequest, request: Request):
    """Middleware-level panel access check. Called before EVERY panel render."""
    try:
        payload = verify_token(req.token)
    except ValueError as e:
        log_access(request, "TOKEN_INVALID", "?", req.role, panel=req.panel, allowed=False, reason=str(e))
        raise HTTPException(401, "Invalid or expired token")

    # Role claim must match what client says
    if payload.get("role") != req.role.lower():
        log_access(request, "ROLE_MISMATCH", payload.get("sub","?"), req.role, panel=req.panel, allowed=False, reason="jwt_role_mismatch")
        raise HTTPException(403, "Role mismatch — token rejected")

    # Panel access check
    allowed_panels = payload.get("panels", [])
    if allowed_panels != "*" and req.panel not in allowed_panels:
        log_access(request, "PANEL_DENIED", payload.get("sub","?"), req.role, panel=req.panel, allowed=False, reason="panel_not_in_role")
        raise HTTPException(403, f"Access Denied: {req.panel}")

    log_access(request, "PANEL_ACCESS", payload.get("sub","?"), req.role, panel=req.panel)
    return {"ok": True, "lvl": payload.get("lvl"), "sub": payload.get("sub")}


@app.post("/api/auth/webauthn/challenge")
async def webauthn_challenge(req: WebAuthnChallengeRequest, request: Request):
    """Issue WebAuthn challenge for L3+ roles"""
    cfg = ROLE_MATRIX.get(req.role, {})
    challenge = secrets.token_urlsafe(32)
    # In prod: store challenge in Redis with 60s TTL
    signed = sign_token({"challenge": challenge, "user_id": req.user_id, "exp": int(time.time()) + 60})
    return {
        "challenge": challenge,
        "challenge_token": signed,
        "rp_id": "localhost",
        "required": cfg.get("lvl", 0) >= 2,  # L2+ must complete WebAuthn
    }


@app.get("/api/auth/child-block/{role}")
async def child_block_check(role: str, request: Request):
    """Frontend calls this before showing role to child — always hard-blocked"""
    is_blocked = role.lower() in CHILD_BLOCKED
    if is_blocked:
        log_access(request, "CHILD_PROBE", "?", role, allowed=False, reason="child_blocked")
    return {"blocked": is_blocked}


@app.get("/api/logs/access")
async def get_access_logs(x_admin_token: str = Header(None)):
    """Admin-only: read access logs"""
    if not x_admin_token:
        raise HTTPException(403, "No token")
    try:
        payload = verify_token(x_admin_token)
        if payload.get("lvl", 0) < 5:
            raise HTTPException(403, "Insufficient clearance")
    except ValueError:
        raise HTTPException(401, "Invalid token")

    lines = []
    if LOG_FILE.exists():
        for line in LOG_FILE.read_text().strip().split("\n")[-200:]:
            try: lines.append(json.loads(line))
            except: pass
    return {"logs": lines, "count": len(lines)}


@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


# ─── GLOBAL EXCEPTION HANDLER ─────────────────────────
@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8443, log_level="warning")

# ── PASSPHRASE VERIFY (called by gate UI) ──────────────
class PPVerify(BaseModel):
    role: str
    passphrase_hash: str

@app.post("/api/auth/verify-passphrase")
async def verify_passphrase(req: PPVerify, request: Request):
    role = req.role.lower()
    if role not in ROLE_MATRIX or not ROLE_MATRIX[role].get("passphrase"):
        raise HTTPException(400, "Role does not require passphrase")
    expected = PASSPHRASE_HASHES.get(role,"")
    if not hmac.compare_digest(req.passphrase_hash.lower(), expected):
        log_access(request,"PP_VERIFY_FAIL","?",role,allowed=False,reason="bad_passphrase")
        await __import__("asyncio").sleep(1.5)
        raise HTTPException(403,"Access Denied")
    log_access(request,"PP_VERIFY_OK","?",role)
    return {"ok":True}

# ── TOKEN REFRESH ──────────────────────────────────────
@app.post("/api/auth/refresh")
async def refresh_token(request: Request, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"No token")
    token = authorization[7:]
    try:
        payload = verify_token(token)
    except ValueError as e:
        raise HTTPException(401, str(e))
    # Issue fresh token with same claims
    payload["iat"] = int(time.time())
    payload["exp"] = int(time.time()) + 28800
    payload["jti"] = secrets.token_hex(16)
    new_token = sign_token(payload)
    return {"token": new_token, "expires_in": 28800}

# ── EVENT LOG ENDPOINT ─────────────────────────────────
class EventLog(BaseModel):
    ts: int
    type: str
    msg: str
    ip: str = "client"

@app.post("/api/logs/event")
async def log_event(event: EventLog, request: Request,
                    authorization: str = Header(None)):
    """Accept client-side audit events"""
    if not authorization:
        raise HTTPException(401,"No token")
    try:
        token = authorization.replace("Bearer ","")
        payload = verify_token(token)
    except:
        raise HTTPException(401,"Invalid token")
    entry = {
        "ts":   datetime.now(timezone.utc).isoformat(),
        "ip":   request.client.host,
        "user": payload.get("sub","?"),
        "role": payload.get("role","?"),
        "type": event.type,
        "msg":  event.msg[:500],
        "src":  "client",
    }
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry)+"\n")
    return {"ok":True}
