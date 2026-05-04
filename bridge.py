#!/usr/bin/env python3
"""
Sovereignty AI Studio — Bridge Server (ws://localhost:9897)
===========================================================
BridgeServer class-based architecture with:
- Sovereign AI routing (no external SaaS, no Anthropic/OpenAI calls)
- Token validation via token_handler on every client connection
- Persistent interaction memory via memory.hydration
- Context injection: each AI request is augmented with prior session memory
- broadcast_ai_response helper
- Graceful shutdown via stop()

All AI requests route through ai_core.sovereign_bridge.
"""

import asyncio
import hashlib
import json
import logging
import os
import pathlib
import sys
import time
import urllib.request

try:
    import websockets
    from websockets.server import serve

    WS_OK = True
except ImportError:
    WS_OK = False
    print("WARNING: websockets not installed. Run: pip3 install websockets")

PORT = int(os.environ.get("SG_PORT", 9897))
HOST = os.environ.get("SG_HOST", "localhost")
SOVEREIGN_API_URL = os.environ.get(
    "SOVEREIGN_API_URL", "http://localhost:8000/api/ai"
).rstrip("/")

# When True, every connecting WebSocket client must supply a valid JWT in
# the "token" field of their first message.  Disable in development with
# BRIDGE_REQUIRE_TOKEN=0 in your .env.
REQUIRE_TOKEN = os.environ.get("BRIDGE_REQUIRE_TOKEN", "0").strip() not in ("0", "false", "")

ROOT_DIR = pathlib.Path(__file__).parent
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "bridge.log"),
    ],
)
log = logging.getLogger("bridge")


def sha256(data: str) -> str:
    """Return the SHA-256 hex digest of *data*."""
    return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Optional integrations — imported lazily so bridge.py still works in minimal
# environments where not all dependencies are installed.
# ---------------------------------------------------------------------------

def _load_token_manager():
    """Return a TokenManager instance or None if unavailable."""
    try:
        from token_handler import TokenManager
        return TokenManager()
    except Exception as exc:  # noqa: BLE001
        log.debug("TokenManager not available: %s", exc)
        return None


def _load_hydration():
    """Return a MemoryHydration instance or None if unavailable."""
    try:
        from memory import MemoryHydration
        return MemoryHydration()
    except Exception as exc:  # noqa: BLE001
        log.debug("MemoryHydration not available: %s", exc)
        return None


class BridgeServer:
    """Encapsulates WebSocket server, client handling, AI routing, and broadcast.

    On first start the server:
    1. Hydrates the memory context from persistent storage.
    2. Optionally validates client tokens via TokenManager.
    3. Injects memory context into AI system prompts.
    4. Records each AI interaction back to persistent memory.

    Args:
        host: Bind address.  Defaults to the ``SG_HOST`` environment variable.
        port: Bind port.  Defaults to the ``SG_PORT`` environment variable.
    """

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.clients: set = set()
        self._server = None
        self._stopping = False

        # Lazy-loaded subsystems — set in start() so they can be async
        self._token_manager = None   # TokenManager | None
        self._hydration = None       # MemoryHydration | None
        self._hydrated = False

    # ------------------------------------------------------------------
    # Boot-time setup
    # ------------------------------------------------------------------

    async def _setup_integrations(self) -> None:
        """Load token manager and memory hydration on server startup."""
        self._token_manager = _load_token_manager()
        if self._token_manager:
            log.info("Bridge: TokenManager loaded.")

        self._hydration = _load_hydration()
        if self._hydration:
            try:
                await self._hydration.hydrate(agent_ids=["bridge"])
                self._hydrated = True
                log.info("Bridge: memory hydration complete.")
            except Exception as exc:  # noqa: BLE001
                log.warning("Bridge: memory hydration failed: %s", exc)

    # ------------------------------------------------------------------
    # Transport helpers
    # ------------------------------------------------------------------

    async def send(self, ws, obj: dict) -> None:
        """Send a JSON-serialised *obj* to a single WebSocket client."""
        try:
            await ws.send(json.dumps(obj))
        except Exception as e:
            log.warning("Send error: %s", e)

    async def broadcast(self, obj: dict, exclude=None) -> None:
        """Send *obj* to all connected clients, optionally skipping *exclude*."""
        for client in list(self.clients):
            if client is not exclude:
                await self.send(client, obj)

    async def broadcast_ai_response(
        self, agent: str, reply: str, context: str, exclude=None
    ) -> None:
        """Broadcast a structured AI response payload to all clients.

        Args:
            agent:   Name of the agent that produced the reply.
            reply:   AI-generated text response.
            context: Opaque context string echoed from the client request.
            exclude: WebSocket to exclude from the broadcast (typically the
                     originating client, who already received the response).
        """
        payload = {
            "type": "ai_response",
            "agent": agent,
            "text": reply,
            "context": context,
            "hash": sha256(reply),
            "ts": int(time.time() * 1000),
        }
        await self.broadcast(payload, exclude=exclude)

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    def _validate_token(self, token: str) -> bool:
        """Return True if *token* is a valid, non-expired JWT.

        When no TokenManager is loaded (lightweight mode) all tokens are
        accepted to preserve backward compatibility.
        """
        if not self._token_manager:
            return True
        try:
            self._token_manager.validate(token)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("Bridge: token validation failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    def _get_memory_context(self, agent: str) -> str:
        """Return the hydrated memory context string for *agent*.

        Returns an empty string when hydration is not available.
        """
        if not self._hydration:
            return ""
        return self._hydration.get_context(agent)

    async def _record_interaction(
        self, agent: str, user_msg: str, ai_reply: str
    ) -> None:
        """Persist an AI interaction asynchronously (fire-and-forget)."""
        if not self._hydration:
            return
        try:
            await self._hydration.record_interaction(
                agent=agent,
                user_msg=user_msg,
                ai_reply=ai_reply,
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("Bridge: could not record interaction: %s", exc)

    # ------------------------------------------------------------------
    # AI routing
    # ------------------------------------------------------------------

    async def _chat_sovereign(
        self, msg: str, sys_prompt: str, agent: str = "sovereign"
    ) -> str:
        """Route to the local sovereign AI bridge — no external SaaS.

        Falls back to the HTTP sovereign API endpoint when the Python
        module is unavailable.
        """
        try:
            from ai_core.sovereign_bridge import SovereignBridge

            bridge = SovereignBridge()
            messages = []
            if sys_prompt:
                messages.append({"role": "system", "content": sys_prompt})
            messages.append({"role": "user", "content": msg})
            return bridge.chat(messages)
        except Exception as e:  # noqa: BLE001
            log.warning("Sovereign bridge failed, falling back to HTTP: %s", e)

        # HTTP fallback to the sovereign API endpoint
        try:
            messages = [{"role": "user", "content": msg}]
            if sys_prompt:
                messages.insert(0, {"role": "system", "content": sys_prompt})
            body = json.dumps({
                "messages": messages,
                "max_tokens": 2048,
                "context": {"agent": agent},
            }).encode()
            req = urllib.request.Request(
                f"{SOVEREIGN_API_URL}/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
                return (
                    data.get("text")
                    or data.get("response")
                    or (data.get("choices", [{}])[0].get("message", {}).get("content", ""))
                    or "[no response]"
                )
        except Exception as e:  # noqa: BLE001
            log.error("Sovereign API error: %s", e)
            return f"[Sovereign bridge error: {e}]"

    async def ai_chat(
        self, ws, msg: str, agent: str, context: str, system: str = ""
    ) -> None:
        """Handle an ``ai_chat`` message: inject memory context, call AI, record result.

        Args:
            ws:      The originating WebSocket client.
            msg:     User's message text.
            agent:   Agent identifier (used for memory scoping).
            context: Opaque context string from the client request.
            system:  Optional custom system prompt override.
        """
        # Build system prompt, optionally injecting prior memory context
        memory_context = self._get_memory_context(agent)
        base_prompt = system or (
            "You are a sovereign AI assistant running entirely on self-hosted "
            "infrastructure. No data leaves the network. Be precise and "
            "production-ready. Never fabricate data, and cite uncertainty when unsure."
        )
        if memory_context:
            sys_prompt = f"{base_prompt}\n\n{memory_context}"
        else:
            sys_prompt = base_prompt

        reply = await self._chat_sovereign(msg, sys_prompt, agent)

        log.info("%s response: %s...", agent, reply[:50])
        await self.send(
            ws,
            {
                "type": "ai_response",
                "agent": agent,
                "text": reply,
                "context": context,
                "hash": sha256(reply),
                "ts": int(time.time() * 1000),
            },
        )
        await self.broadcast_ai_response(agent, reply, context, exclude=ws)

        # Persist interaction to memory (non-blocking — errors are swallowed)
        asyncio.create_task(self._record_interaction(agent, msg, reply))

    # ------------------------------------------------------------------
    # Client handling
    # ------------------------------------------------------------------

    async def handle_client(self, ws) -> None:
        """Handle the full lifecycle of a single WebSocket client connection.

        Protocol:
        - Clients *may* send a ``{"type": "auth", "token": "..."}`` message
          as their first message when ``BRIDGE_REQUIRE_TOKEN=1``.
        - All subsequent messages follow the existing ``ai_chat`` protocol.
        """
        self.clients.add(ws)
        addr = ws.remote_address
        log.info("Client connected: %s | total=%s", addr, len(self.clients))

        authenticated = not REQUIRE_TOKEN  # True when auth is disabled

        try:
            async for raw in ws:
                try:
                    message = json.loads(raw)
                except Exception:
                    continue

                mtype = message.get("type", "")

                # ── Token authentication handshake ─────────────────────
                if mtype == "auth":
                    token = message.get("token", "")
                    if self._validate_token(token):
                        authenticated = True
                        await self.send(ws, {"type": "auth_ok"})
                        log.info("Client %s authenticated successfully.", addr)
                    else:
                        await self.send(ws, {"type": "auth_error", "msg": "Invalid token"})
                        log.warning("Client %s failed authentication — closing.", addr)
                        return
                    continue

                # ── Require auth before any other message type ──────────
                if not authenticated:
                    await self.send(
                        ws,
                        {"type": "auth_required", "msg": "Send {type:auth, token:...} first"},
                    )
                    continue

                # ── AI chat ─────────────────────────────────────────────
                if mtype == "ai_chat":
                    agent = message.get("agent", "claude")
                    msg = message.get("message", "")
                    context = message.get("context", "")
                    system = message.get("system", "")
                    asyncio.create_task(self.ai_chat(ws, msg, agent, context, system))
                else:
                    log.debug("Unhandled message type: %s", mtype)

        except Exception as e:
            log.warning("Client %s error: %s", addr, e)
        finally:
            self.clients.discard(ws)
            log.info("Client disconnected: %s | total=%s", addr, len(self.clients))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the WebSocket server.  Blocks until cancelled."""
        if not WS_OK:
            log.error("FATAL: websockets is not installed.")
            sys.exit(1)

        # Load memory hydration and token manager before accepting connections
        await self._setup_integrations()

        log.info("Bridge starting on ws://%s:%s", self.host, self.port)
        self._server = await serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=30,
            max_size=50 * 1024 * 1024,
        )
        log.info("Bridge LIVE → ws://%s:%s", self.host, self.port)
        if REQUIRE_TOKEN:
            log.info("Bridge: token authentication ENABLED.")
        else:
            log.info("Bridge: token authentication disabled (set BRIDGE_REQUIRE_TOKEN=1 to enable).")
        await asyncio.Future()  # intentional: keep server alive until cancellation/interruption

    async def stop(self) -> None:
        """Close all client connections and shut down the server cleanly."""
        log.info("Stopping BridgeServer...")
        self._stopping = True
        for client in list(self.clients):
            await client.close()
        self.clients.clear()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        log.info("BridgeServer stopped.")


async def _main():
    server = BridgeServer()
    try:
        await server.start()
    finally:
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nBridge stopped.")
