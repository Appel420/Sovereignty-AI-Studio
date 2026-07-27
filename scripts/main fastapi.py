from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import re
import time
import os
import traceback

# === Sovereign Persistent Brain ===
from sovereign_persistent_brain.scripts.hydrate_brain import hydrate_brain
from sovereign_persistent_brain.scripts.persist_brain import persist_brain
from sovereign_persistent_brain.scripts.register_agent import register_agent
from sovereign_persistent_brain.scripts.dispatch_event import dispatch_event
from sovereign_persistent_brain.scripts.handle_error import handle_error
from sovereign_persistent_brain.scripts.self_sustain_loop import self_sustain_loop

app = FastAPI(title="XAI LiveTerminal + Sovereign Persistent Brain")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:9898", "http://localhost:9898",
                   "http://127.0.0.1:9897", "http://localhost:9897"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── AI provider imports (lazy) ─────────────────────────────────────────────
def _get_key(agent: str) -> str:
    """Load key from env → sgh_keys.json. Never from browser."""
    from pathlib import Path
    aliases = {"anthropic": "claude", "gpt": "openai", "grok": "xai"}
    a = aliases.get(agent, agent)
    # Env vars first
    env_map = {
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "xai":    "XAI_API_KEY",
    }
    v = os.getenv(env_map.get(a, ""), "")
    if v:
        return v
    # sgh_keys.json
    keys_file = Path(os.getenv("KEYS_FILE", "sgh_keys.json"))
    if keys_file.exists():
        try:
            data = json.loads(keys_file.read_text())
            return data.get(a) or data.get(agent) or ""
        except Exception:
            pass
    return ""


async def _call_ai(messages: list, agent: str = "claude") -> tuple[str | None, str | None]:
    """Route to local AI provider using server-side keys only."""
    import aiohttp
    a = agent.lower()
    key = _get_key(a)

    if a in ("claude", "anthropic"):
        if not key:
            # Try xAI as fallback
            return await _call_ai(messages, "xai")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
        body = {"model": "claude-sonnet-4-5", "max_tokens": 8192, "messages": messages}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    "https://api.anthropic.com/v1/messages",
                    json=body, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as r:
                    d = await r.json()
                    if r.status != 200:
                        err = d.get("error", {}).get("message", f"HTTP {r.status}")
                        return None, err
                    return d["content"][0]["text"], None
        except Exception as e:
            return None, str(e)

    elif a in ("xai", "grok"):
        if not key:
            return None, "No xAI key — set XAI_API_KEY or POST /api/keys"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = {"model": "grok-3", "max_tokens": 8192, "messages": messages}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    "https://api.x.ai/v1/chat/completions",
                    json=body, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as r:
                    d = await r.json()
                    if r.status != 200:
                        return None, d.get("error", {}).get("message", f"HTTP {r.status}")
                    return d["choices"][0]["message"]["content"], None
        except Exception as e:
            return None, str(e)

    elif a in ("openai", "gpt"):
        if not key:
            return None, "No OpenAI key"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = {"model": "gpt-4o", "max_tokens": 4096, "messages": messages}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=body, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as r:
                    d = await r.json()
                    if r.status != 200:
                        return None, d.get("error", {}).get("message", f"HTTP {r.status}")
                    return d["choices"][0]["message"]["content"], None
        except Exception as e:
            return None, str(e)

    # Try all providers
    for ag in ["claude", "xai", "openai"]:
        text, err = await _call_ai(messages, ag)
        if text:
            return text, None
    return None, "No AI providers configured — set keys in sgh_keys.json or env"


def _extract_fence(text: str, lang: str) -> str:
    """Extract code from first fenced block in AI response."""
    m = re.search(rf"```{re.escape(lang)}\n([\s\S]*?)```", text)
    if not m:
        m = re.search(r"```[\w-]*\n([\s\S]*?)```", text)
    return m.group(1).strip() if m else ""


# ── Global brain state ─────────────────────────────────────────────────────
brain_state: dict = {"state": {}, "scarlog": []}


# ── Exception handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    try:
        handle_error(exc, context=f"Global handler: {request.url}")
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": str(exc), "type": type(exc).__name__, "timestamp": time.time()}
    )


# ── Startup ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print("🧠 Initializing Sovereign Persistent Brain...")
    global brain_state
    try:
        brain_state = hydrate_brain()
    except Exception as e:
        print(f"⚠ Brain hydration error: {e} — starting with empty state")
        brain_state = {"state": {}, "scarlog": []}

    try:
        register_agent(
            agent_id="live-terminal",
            capabilities=["websocket", "voice", "command-processing", "pqc-signing"],
            metadata={"version": "2.0", "platform": "web"}
        )
    except Exception as e:
        print(f"⚠ Agent registration: {e}")

    try:
        asyncio.create_task(self_sustain_loop())
    except Exception as e:
        print(f"⚠ Self-sustain loop: {e}")

    print("✅ Sovereign Brain initialized")


# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status":    "healthy",
        "brain":     "active",
        "pqc":       "ML-DSA-65",
        "timestamp": time.time(),
    }


# ══════════════════════════════════════════════════════════════════════
# CODE REVIEW ENDPOINT — used by CodeMaster HTTP fallback
# All AI calls use server-side keys only. Browser sends no credentials.
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/agents/review")
@app.post("/agents/review")
async def agents_review(request):
    """Code analysis + fix. Bridge-local. No browser API keys needed."""
    try:
        d = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    lang  = d.get("lang", "html")
    code  = d.get("code", "")
    mode  = d.get("mode", "fix")
    agent = d.get("agent", "claude")

    if not code.strip():
        raise HTTPException(status_code=400, detail="code is required")

    if mode == "analyze":
        prompt = (
            d.get("prompt") or
            f"Analyze this {lang} code. Find ALL bugs, syntax errors, duplicate functions, "
            f"null stubs, fake implementations, and redundant logic. "
            f"For each issue output: LINE N: [problem] → [fix]. Be exhaustive and precise."
        )
    else:
        prompt = (
            d.get("prompt") or
            f"Fix ALL bugs, syntax errors, duplicate function definitions, null stubs, "
            f"fake/placeholder implementations, and redundant code in this {lang} code. "
            f"Every function must be real and working. No nulls. No stubs. "
            f"End with ONE fenced ```{lang}``` block of the complete fixed source."
        )

    messages = [{"role": "user", "content": f"{prompt}\n\n```{lang}\n{code[:15000]}\n```"}]

    try:
        text, err = await _call_ai(messages, agent)
    except Exception as e:
        text, err = None, str(e)

    fixed_code = _extract_fence(text, lang) if text else ""

    # Log to brain
    try:
        dispatch_event("code_review", {
            "lang": lang, "mode": mode, "lines": len(code.split("\n")),
            "fixed": bool(fixed_code), "agent": agent, "timestamp": time.time()
        })
    except Exception:
        pass

    return {
        "review":     text or err,
        "fixed_code": fixed_code,
        "error":      err,
        "lang":       lang,
        "agent":      agent,
        "timestamp":  time.time(),
    }


# ── Keys endpoint (set AI keys on the server, never in browser) ────────────
@app.post("/api/keys")
async def set_keys(request):
    """Store AI provider keys in sgh_keys.json. Browser sends key once; stored locally."""
    from pathlib import Path
    try:
        d = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    keys_file = Path(os.getenv("KEYS_FILE", "sgh_keys.json"))
    existing: dict = {}
    if keys_file.exists():
        try:
            existing = json.loads(keys_file.read_text())
        except Exception:
            pass

    saved = []
    for agent, key in d.items():
        if agent and key and isinstance(key, str):
            existing[agent] = key
            saved.append(agent)

    keys_file.write_text(json.dumps(existing, indent=2))
    return {"status": "ok", "saved": saved}


@app.get("/api/keys")
async def get_keys():
    """Return which keys are configured (boolean only — never expose values)."""
    from pathlib import Path
    keys_file = Path(os.getenv("KEYS_FILE", "sgh_keys.json"))
    configured: dict = {}
    if keys_file.exists():
        try:
            data = json.loads(keys_file.read_text())
            configured = {k: bool(v) for k, v in data.items()}
        except Exception:
            pass
    # Also check env
    for name, env in [("claude", "ANTHROPIC_API_KEY"), ("xai", "XAI_API_KEY"), ("openai", "OPENAI_API_KEY")]:
        if os.getenv(env):
            configured[name] = True
    return configured


# ── WebSocket ──────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔌 WS client connected")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                command = message.get("command", data)
            except json.JSONDecodeError:
                command = data

            dispatch_event("user_command", {
                "command": command, "source": "live-terminal", "timestamp": time.time()
            })

            try:
                response = await process_command(command)
                await websocket.send_text(response)
            except Exception as e:
                handle_error(e, context=f"process_command: {command}")
                await websocket.send_text(json.dumps({
                    "error": True, "message": str(e), "timestamp": time.time()
                }))

    except WebSocketDisconnect:
        print("🔌 WS client disconnected")
    except Exception as e:
        handle_error(e, context="websocket_endpoint")
        try:
            await websocket.close()
        except Exception:
            pass


# ── Command processor ──────────────────────────────────────────────────────
async def process_command(command: str) -> str:
    command = command.strip()
    cmd_lower = command.lower()

    try:
        if cmd_lower.startswith("sign "):
            message_text = command[5:].strip()
            if not message_text:
                return "❌ Usage: sign <message>"
            from sovereign_persistent_brain.scripts.persist_brain import signer
            signature = signer.sign(message_text.encode())
            result = {
                "action": "sign", "message": message_text,
                "signature": signature.hex(), "algorithm": "ML-DSA-65", "timestamp": time.time()
            }
            persist_brain(brain_state["state"], new_logs=[{"type": "pqc_sign", "message": message_text[:60]}])
            return json.dumps(result, indent=2)

        elif cmd_lower.startswith("verify "):
            try:
                data = json.loads(command[7:].strip())
                signature = bytes.fromhex(data["signature"])
                msg_bytes = data["message"].encode()
                public_key = bytes.fromhex(data["public_key"])
                from oqs import Signature
                verifier = Signature("ML-DSA-65")
                is_valid = verifier.verify(msg_bytes, signature, public_key)
                return json.dumps({"action": "verify", "valid": is_valid, "algorithm": "ML-DSA-65"}, indent=2)
            except Exception as e:
                return f"❌ Verification error: {e}"

        elif cmd_lower in ("status", "brain", "brain status"):
            agent_count = 0
            agents_file = "brain/agents.json"
            if os.path.exists(agents_file):
                with open(agents_file) as f:
                    agent_count = len(json.load(f))
            # Show which AI keys are configured (boolean only)
            configured_keys = []
            for name, env in [("claude", "ANTHROPIC_API_KEY"), ("xai", "XAI_API_KEY"), ("openai", "OPENAI_API_KEY")]:
                if _get_key(name):
                    configured_keys.append(name)
            return json.dumps({
                "brain_status":       "Active",
                "pqc_algorithm":      "ML-DSA-65",
                "scarlog_entries":    len(brain_state["scarlog"]),
                "registered_agents":  agent_count,
                "ai_keys_configured": configured_keys,
                "timestamp":          time.time()
            }, indent=2)

        elif cmd_lower == "rotate keys":
            from sovereign_persistent_brain.scripts.rotate_keys import rotate_keys
            return json.dumps(rotate_keys(), indent=2)

        elif cmd_lower == "rotate tokens":
            from sovereign_persistent_brain.scripts.rotate_tokens import rotate_tokens
            return json.dumps(rotate_tokens(), indent=2)

        elif cmd_lower == "agents":
            agents_file = "brain/agents.json"
            if os.path.exists(agents_file):
                with open(agents_file) as f:
                    return json.dumps(json.load(f), indent=2)
            return "No agents registered."

        elif cmd_lower.startswith("dispatch "):
            parts = command[9:].split(" ", 1)
            if len(parts) < 2:
                return "❌ Usage: dispatch <event_type> <json_data>"
            event_type = parts[0]
            try:
                event_data = json.loads(parts[1])
            except Exception:
                event_data = {"raw": parts[1]}
            event = dispatch_event(event_type, event_data)
            return json.dumps(event, indent=2)

        elif cmd_lower.startswith("register "):
            agent_id = command[9:].strip()
            if not agent_id:
                return "❌ Usage: register <agent_id>"
            register_agent(agent_id, capabilities=["websocket", "command"])
            return f"✅ Agent '{agent_id}' registered"

        else:
            return (
                f"✅ Command received: {command}\n\n"
                "Available commands:\n"
                "  sign <message>       — PQC ML-DSA-65 sign\n"
                "  verify <json>        — verify signature\n"
                "  status               — brain + AI key status\n"
                "  rotate keys          — rotate PQC keys\n"
                "  rotate tokens        — rotate tokens\n"
                "  agents               — list registered agents\n"
                "  dispatch <type> <j>  — dispatch brain event\n"
                "  register <id>        — register an agent"
            )

    except Exception as e:
        handle_error(e, context=f"process_command: {command}")
        return f"❌ Error: {e}"
