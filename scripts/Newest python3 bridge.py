#!/usr/bin/env python3
"""
python3_bridge.py — Sovereignty AI Studio
Python 3 bridge: HTTP + WebSocket on port 9897.
Pure stdlib + aiohttp. Runs in iSH, a-Shell, macOS, Linux, Docker.

Port map:
  9897  This server   WS + HTTP  (AI bus, agents, Piper, BLAKE3)
  9898  KODER         HTTP only  (serves SGHv119.html — static)
  9899  Node bridge   WS + HTTP  (external gateway)
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ── Auto-install aiohttp if missing ──────────────────────────────
try:
    from aiohttp import web
    import aiohttp
except ImportError:
    print("[bridge] Installing aiohttp...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "aiohttp", "-q",
         "--break-system-packages"],
        stderr=subprocess.DEVNULL,
    )
    from aiohttp import web
    import aiohttp

# ── BLAKE3 (optional — SHA3-256 fallback) ────────────────────────
try:
    import blake3 as _blake3
    def _hash(data: str | bytes) -> str:
        if isinstance(data, str): data = data.encode()
        return _blake3.blake3(data).hexdigest()
    HASH_ALGO = "blake3"
except ImportError:
    def _hash(data: str | bytes) -> str:
        if isinstance(data, str): data = data.encode()
        return hashlib.sha3_256(data).hexdigest()
    HASH_ALGO = "sha3-256"

# ── Config ────────────────────────────────────────────────────────
PORT        = int(os.getenv("PORT", 9897))
HOST        = os.getenv("HOST", "127.0.0.1")
LOG_LEVEL   = os.getenv("LOG_LEVEL", "INFO")
HTML_FILE   = os.getenv("SGH_HTML", "SGHv119.html")
KEYS_FILE   = Path(os.getenv("KEYS_FILE", "sgh_keys.json"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [bridge] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bridge")

# ── API keys (env → file → runtime) ──────────────────────────────
def _load_keys() -> dict:
    keys: dict = {}
    for name, env in [
        ("claude",  "ANTHROPIC_API_KEY"),
        ("openai",  "OPENAI_API_KEY"),
        ("xai",     "XAI_API_KEY"),
        ("grok",    "GROK_API_KEY"),
    ]:
        v = os.getenv(env, "")
        if v: keys[name] = v
    if KEYS_FILE.exists():
        try:
            stored = json.loads(KEYS_FILE.read_text())
            for k, v in stored.items():
                if v and k not in keys:
                    keys[k] = v
        except Exception:
            pass
    return keys

KEYS: dict = _load_keys()

def _save_keys():
    KEYS_FILE.write_text(json.dumps(KEYS, indent=2))

def _get_key(agent: str) -> str:
    aliases = {"anthropic": "claude", "gpt": "openai", "grok": "xai"}
    return KEYS.get(agent) or KEYS.get(aliases.get(agent, "")) or ""

# ── WebSocket clients ─────────────────────────────────────────────
WS_CLIENTS: set = set()

async def _broadcast(msg: dict):
    data = json.dumps(msg)
    dead = set()
    for ws in list(WS_CLIENTS):
        try:
            await ws.send_str(data)
        except Exception:
            dead.add(ws)
    WS_CLIENTS.difference_update(dead)

# ── AI routing ────────────────────────────────────────────────────
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL    = "https://api.openai.com/v1/chat/completions"
XAI_URL       = "https://api.x.ai/v1/chat/completions"

async def _call_claude(messages: list, system: str = "", model: str = "claude-sonnet-4-5", max_tokens: int = 8192) -> tuple[Optional[str], Optional[str]]:
    key = _get_key("claude")
    if not key:
        return None, "No Claude API key — set ANTHROPIC_API_KEY or use /api/keys"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    body: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(ANTHROPIC_URL, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as r:
                d = await r.json()
                if r.status != 200:
                    return None, d.get("error", {}).get("message", f"HTTP {r.status}")
                return d["content"][0]["text"], None
    except Exception as e:
        return None, str(e)

async def _call_openai(messages: list, model: str = "gpt-4o", max_tokens: int = 4096) -> tuple[Optional[str], Optional[str]]:
    key = _get_key("openai")
    if not key:
        return None, "No OpenAI API key"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body    = {"model": model, "max_tokens": max_tokens, "messages": messages}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(OPENAI_URL, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as r:
                d = await r.json()
                if r.status != 200:
                    return None, d.get("error", {}).get("message", f"HTTP {r.status}")
                return d["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)

async def _call_xai(messages: list, model: str = "grok-3", max_tokens: int = 8192) -> tuple[Optional[str], Optional[str]]:
    key = _get_key("xai") or _get_key("grok")
    if not key:
        return None, "No xAI API key"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body    = {"model": model, "max_tokens": max_tokens, "messages": messages}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(XAI_URL, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as r:
                d = await r.json()
                if r.status != 200:
                    return None, d.get("error", {}).get("message", f"HTTP {r.status}")
                return d["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)

async def _route_ai(agent: str, messages: list, system: str = "") -> tuple[Optional[str], Optional[str]]:
    a = (agent or "claude").lower()
    if a in ("claude", "anthropic"):
        return await _call_claude(messages, system=system)
    if a in ("gpt", "openai", "chatgpt"):
        return await _call_openai(messages)
    if a in ("grok", "xai"):
        return await _call_xai(messages)
    # Try all in order
    for fn in [_call_claude, _call_openai, _call_xai]:
        text, err = await fn(messages)
        if text:
            return text, None
    return None, "No AI keys configured — POST /api/keys to set them"

# ── Execute (allowlist) ───────────────────────────────────────────
ALLOWED_TOOLS = {
    "echo", "ls", "cat", "pwd", "whoami", "uname",
    "python3", "python", "node", "npm", "git",
    "curl", "ping", "blake3", "pytest", "flake8",
}

def _exec_tool(cmd: str) -> dict:
    parts = cmd.strip().split()
    if not parts:
        return {"status": "error", "stdout": "", "stderr": "empty command"}
    tool = Path(parts[0]).name
    if tool not in ALLOWED_TOOLS:
        return {
            "status": "denied",
            "stdout": "",
            "stderr": f"'{tool}' not in allowlist: {sorted(ALLOWED_TOOLS)}",
        }
    try:
        r = subprocess.run(parts, capture_output=True, text=True, timeout=30)
        return {"status": "success" if r.returncode == 0 else "error",
                "stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "stdout": "", "stderr": "Command timed out (30s)"}
    except FileNotFoundError:
        return {"status": "not_found", "stdout": "", "stderr": f"'{parts[0]}' not found on PATH"}
    except Exception as e:
        return {"status": "error", "stdout": "", "stderr": str(e)}

# ── TTS ───────────────────────────────────────────────────────────
def _tts_speak(text: str) -> dict:
    for cmd in [["say", text], ["espeak", text], ["espeak-ng", text]]:
        try:
            subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
            return {"status": "ok", "engine": cmd[0]}
        except FileNotFoundError:
            continue
    return {"status": "fallback", "note": "No TTS binary found — use browser speechSynthesis"}

# ════════════════════════════════════════════════════════════════
# HTTP handlers
# ════════════════════════════════════════════════════════════════

async def handle_root(req: web.Request) -> web.Response:
    """Serve SGHv119.html at /"""
    for path in [HTML_FILE, f"../{HTML_FILE}", Path(__file__).parent / HTML_FILE]:
        p = Path(path)
        if p.exists():
            return web.Response(
                body=p.read_bytes(),
                content_type="text/html",
                headers={"Cache-Control": "no-cache"},
            )
    return web.Response(status=404, text=f"{HTML_FILE} not found")

async def handle_health(req: web.Request) -> web.Response:
    return web.json_response({
        "status":     "healthy",
        "service":    "sovereignty-python-bridge",
        "version":    "2.0",
        "port":       PORT,
        "hash_algo":  HASH_ALGO,
        "ws_clients": len(WS_CLIENTS),
        "keys":       {k: bool(v) for k, v in KEYS.items()},
        "timestamp":  time.time(),
    })

async def handle_ai(req: web.Request) -> web.Response:
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)
    agent   = d.get("agent", "claude")
    prompt  = d.get("prompt", d.get("message", ""))
    system  = d.get("system", "")
    history = d.get("history", [])
    messages = history + [{"role": "user", "content": prompt}]
    text, err = await _route_ai(agent, messages, system)
    return web.json_response({
        "response": text,
        "error":    err,
        "agent":    agent,
        "timestamp": time.time(),
    })

async def handle_agents_chat(req: web.Request) -> web.Response:
    """Alias: /agents/chat"""
    return await handle_ai(req)

async def handle_agents_review(req: web.Request) -> web.Response:
    """Code review + fix endpoint — used by CodeMaster HTTP fallback.
    Extracts fixed_code from fenced block so client can apply it directly."""
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)

    lang   = d.get("lang", "html")
    code   = d.get("code", "")
    mode   = d.get("mode", "fix")   # "analyze" | "fix"
    agent  = d.get("agent", "claude")

    if mode == "analyze":
        prompt = (
            d.get("prompt") or
            f"Analyze this {lang} code. Find ALL bugs, syntax errors, duplicate functions, "
            f"null stubs, fake implementations, and redundant logic. "
            f"For each issue output: LINE N: [problem] → [fix]. Be exhaustive."
        )
    else:
        prompt = (
            d.get("prompt") or
            f"You are a senior software engineer. Fix ALL bugs, syntax errors, duplicate "
            f"function definitions, null stubs, fake/placeholder implementations, and "
            f"redundant code in this {lang} code. "
            f"End with ONE fenced ```{lang}``` block containing the complete fixed source."
        )

    messages = [{"role": "user", "content": f"{prompt}\n\n```{lang}\n{code[:15000]}\n```"}]

    # Route to available AI provider
    text, err = await _route_ai(agent, messages)

    # Extract fixed code from fenced block
    fixed_code = ""
    if text:
        import re
        m = re.search(rf"```{re.escape(lang)}\n([\s\S]*?)```", text)
        if not m:
            m = re.search(r"```[\w-]*\n([\s\S]*?)```", text)
        if m:
            fixed_code = m.group(1).strip()

    return web.json_response({
        "review":     text or err,
        "fixed_code": fixed_code,
        "error":      err,
        "lang":       lang,
        "agent":      agent,
        "timestamp":  time.time(),
    })

async def handle_exec(req: web.Request) -> web.Response:
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)
    cmd = d.get("cmd", d.get("command", ""))
    if not cmd:
        return web.json_response({"error": "cmd required"}, status=400)
    result = _exec_tool(cmd)
    status = 200 if result["status"] in ("success",) else 400 if result["status"] == "denied" else 500
    return web.json_response(result, status=status)

async def handle_keys_get(req: web.Request) -> web.Response:
    return web.json_response({k: bool(v) for k, v in KEYS.items()})

async def handle_keys_post(req: web.Request) -> web.Response:
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)
    saved = []
    for agent, key in d.items():
        if agent and key:
            KEYS[agent] = key
            saved.append(agent)
    _save_keys()
    await _broadcast({"type": "keys_updated", "agents": saved})
    return web.json_response({"status": "ok", "saved": saved})

async def handle_speak(req: web.Request) -> web.Response:
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)
    text = d.get("text", "")
    return web.json_response(_tts_speak(text))

async def handle_hash(req: web.Request) -> web.Response:
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)
    data = d.get("data", d.get("text", ""))
    return web.json_response({"hash": _hash(data), "algo": HASH_ALGO})

async def handle_static(req: web.Request) -> web.Response:
    fname = req.match_info.get("filename", "")
    for base in [Path("."), Path("static")]:
        p = base / fname
        if p.exists() and p.is_file():
            ct = "application/wasm" if fname.endswith(".wasm") else "application/octet-stream"
            return web.Response(body=p.read_bytes(), content_type=ct)
    return web.Response(status=404)

# ════════════════════════════════════════════════════════════════
# WebSocket handler
# ════════════════════════════════════════════════════════════════

async def handle_ws(req: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(req)
    WS_CLIENTS.add(ws)
    log.info("WS connected  clients=%d", len(WS_CLIENTS))

    await ws.send_str(json.dumps({
        "type":       "welcome",
        "service":    "sovereignty-python-bridge",
        "version":    "2.0",
        "port":       PORT,
        "hash_algo":  HASH_ALGO,
        "keys":       {k: bool(v) for k, v in KEYS.items()},
    }))

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                d = json.loads(msg.data)
            except Exception:
                continue

            t = d.get("type", "")

            if t == "ping":
                await ws.send_str(json.dumps({"type": "pong", "t": d.get("t")}))

            elif t == "handshake":
                await ws.send_str(json.dumps({
                    "type": "handshake_ack",
                    "server": "sovereignty-python-bridge v2.0",
                    "hash_algo": HASH_ALGO,
                }))

            elif t in ("chat", "agent_chat", "agent_request"):
                agent   = d.get("agent", "claude")
                payload = d.get("payload", {})
                message = d.get("message") or payload.get("prompt") or payload.get("message", "")
                system  = d.get("system", "") or payload.get("system", "")
                history = d.get("history", [])
                messages = history + [{"role": "user", "content": message}]

                await ws.send_str(json.dumps({"type": "thinking", "agent": agent}))
                text, err = await _route_ai(agent, messages, system)

                await ws.send_str(json.dumps({
                    "type":    "agent_response",
                    "agent":   agent,
                    "text":    text or err,
                    "payload": {"text": text, "error": err},
                    "error":   err is not None,
                    "context": d.get("context"),
                    "ts":      int(time.time()),
                }))

            elif t in ("ai_code_review", "code_review"):
                lang  = d.get("lang", "html")
                code  = d.get("code", "")
                mode  = d.get("mode", "fix")
                agent = d.get("agent", "claude")

                if mode == "analyze":
                    prompt = d.get("prompt") or (
                        f"Analyze this {lang} code. Find ALL bugs, syntax errors, "
                        f"duplicate functions, null stubs, and redundant logic. "
                        f"For each issue output: LINE N: [problem] → [fix]. Be exhaustive."
                    )
                else:
                    prompt = d.get("prompt") or (
                        f"Fix ALL bugs, syntax errors, duplicate function definitions, "
                        f"null stubs, and redundant code in this {lang} code. "
                        f"End with ONE fenced ```{lang}``` block of the complete fixed source."
                    )

                messages = [{"role": "user", "content": f"{prompt}\n\n```{lang}\n{code[:15000]}\n```"}]
                await ws.send_str(json.dumps({"type": "thinking", "context": "codemaster"}))

                # Try requested agent, then fall back to any available
                text, err = await _route_ai(agent, messages)

                # Extract fixed code from fenced block
                fixed_code = ""
                if text:
                    import re
                    m = re.search(rf"```{re.escape(lang)}\n([\s\S]*?)```", text)
                    if not m:
                        m = re.search(r"```[\w-]*\n([\s\S]*?)```", text)
                    if m:
                        fixed_code = m.group(1).strip()

                await ws.send_str(json.dumps({
                    "type":       "ai_code_review_result",
                    "review":     text or err,
                    "fixed_code": fixed_code,
                    "lang":       lang,
                    "agent":      agent,
                    "context":    d.get("context", "codemaster"),
                    "error":      text is None,
                    "ts":         int(time.time()),
                }))

            elif t == "set_key":
                agent = d.get("agent", "")
                key   = d.get("key", "")
                if agent and key:
                    KEYS[agent] = key
                    _save_keys()
                    await ws.send_str(json.dumps({"type": "key_saved", "agent": agent}))

            elif t in ("execute", "exec"):
                cmd    = d.get("cmd", d.get("command", ""))
                result = _exec_tool(cmd)
                await ws.send_str(json.dumps({"type": "tool_result", "result": result}))

            elif t == "voice_tts":
                text   = d.get("text", "")
                result = _tts_speak(text)
                await ws.send_str(json.dumps({"type": "tts_result", **result}))

            elif t == "hash":
                data = d.get("data", "")
                await ws.send_str(json.dumps({"type": "hash_result", "hash": _hash(data), "algo": HASH_ALGO}))

            elif t == "health":
                await ws.send_str(json.dumps({
                    "type":       "health_response",
                    "status":     "ok",
                    "clients":    len(WS_CLIENTS),
                    "keys":       {k: bool(v) for k, v in KEYS.items()},
                    "hash_algo":  HASH_ALGO,
                }))

        elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
            break

    WS_CLIENTS.discard(ws)
    log.info("WS disconnected  clients=%d", len(WS_CLIENTS))
    return ws

# ── CORS middleware ───────────────────────────────────────────────
@web.middleware
async def cors(req: web.Request, handler):
    if req.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,x-api-key",
        })
    try:
        resp = await handler(req)
    except web.HTTPException as e:
        resp = web.Response(status=e.status, text=e.reason)
    except Exception as e:
        log.exception("Unhandled error: %s", e)
        resp = web.json_response({"error": str(e)}, status=500)
    resp.headers.update({
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,x-api-key",
    })
    return resp

# ── App ───────────────────────────────────────────────────────────
def make_app() -> web.Application:
    app = web.Application(middlewares=[cors])
    app.router.add_get  ("/",                  handle_root)
    app.router.add_get  ("/SGHv119.html",      handle_root)
    app.router.add_get  ("/api/health",        handle_health)
    app.router.add_get  ("/health",            handle_health)
    app.router.add_post ("/api/ai",            handle_ai)
    app.router.add_post ("/api/chat",          handle_ai)
    app.router.add_post ("/agents/chat",       handle_agents_chat)
    app.router.add_post ("/agents/review",     handle_agents_review)
    app.router.add_post ("/api/agents/chat",   handle_agents_chat)
    app.router.add_post ("/api/agents/review", handle_agents_review)
    app.router.add_post ("/api/exec",          handle_exec)
    app.router.add_get  ("/api/keys",          handle_keys_get)
    app.router.add_post ("/api/keys",          handle_keys_post)
    app.router.add_post ("/api/speak",         handle_speak)
    app.router.add_post ("/voice/tts",         handle_speak)
    app.router.add_post ("/api/hash",          handle_hash)
    app.router.add_get  ("/ws",                handle_ws)
    app.router.add_get  ("/ws/terminal",       handle_ws)  # alias for terminal clients
    app.router.add_get  ("/terminal",          handle_ws)  # alias
    app.router.add_get  ("/static/{filename}", handle_static)
    return app

# ── Main ──────────────────────────────────────────────────────────
async def main():
    app    = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site   = web.TCPSite(runner, HOST, PORT)
    await site.start()

    # Detect LAN IP for iSH users (their loopback ≠ Safari's loopback)
    lan_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print()
    print("══════════════════════════════════════════")
    print("  Sovereignty AI Studio — Python Bridge")
    print("══════════════════════════════════════════")
    print(f"  HTTP  http://{HOST}:{PORT}/")
    print(f"  WS    ws://{HOST}:{PORT}/ws")
    if lan_ip != "127.0.0.1":
        print(f"  LAN   ws://{lan_ip}:{PORT}/ws  ← use if iSH")
    print(f"  Hash  {HASH_ALGO}")
    print(f"  Keys  {', '.join(k for k,v in KEYS.items() if v) or 'none — POST /api/keys'}")
    print(f"  Dashboard  http://127.0.0.1:9898/SGHv119.html")
    print("══════════════════════════════════════════")
    print("  Ctrl+C to stop")
    print()

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await runner.cleanup()
        print("\n[bridge] stopped.")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--host", default=HOST)
    args = ap.parse_args()
    PORT = args.port
    HOST = args.host
    asyncio.run(main())
