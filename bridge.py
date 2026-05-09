#!/usr/bin/env python3
"""
Sovereignty AI Studio — Bridge Server (ws://localhost:9897)
BridgeServer class-based architecture with:
- Sovereign AI routing (no external SaaS, no Anthropic/OpenAI calls)
- Persistent memory with hydration (memory.MemoryStore + MemoryHydrator)
- Token handler integration (token_handler.TokenManager)
- Event bus + watchers (watchers.EventBus, BridgeWatcher, MemoryWatcher)
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
    return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Optional module imports (graceful fallback if packages missing)
# ---------------------------------------------------------------------------

def _try_import_memory():
    try:
        from memory.store import MemoryStore
        from memory.hydration import MemoryHydrator
        return MemoryStore, MemoryHydrator
    except ImportError as e:
        log.warning("memory module not available: %s", e)
        return None, None


def _try_import_token_handler():
    try:
        from token_handler.manager import TokenManager
        return TokenManager
    except ImportError as e:
        log.warning("token_handler module not available: %s", e)
        return None


def _try_import_watchers():
    try:
        from watchers.event_bus import EventBus
        from watchers.bridge_watcher import BridgeWatcher
        from watchers.memory_watcher import MemoryWatcher
        return EventBus, BridgeWatcher, MemoryWatcher
    except ImportError as e:
        log.warning("watchers module not available: %s", e)
        return None, None, None


class BridgeServer:
    """
    Encapsulates WebSocket server, client handling, AI routing,
    persistent memory, token management, and event watchers.
    """

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.clients: set = set()
        self._server = None
        self._stopping = False

        # Memory
        MemoryStore, MemoryHydrator = _try_import_memory()
        self.memory = MemoryStore() if MemoryStore else None
        self.hydrator = MemoryHydrator(self.memory) if (MemoryHydrator and self.memory) else None

        # Token handler
        TokenManager = _try_import_token_handler()
        self.tokens = TokenManager() if TokenManager else None
        if self.tokens:
            self.tokens.import_from_env(os.environ)

        # Watchers / event bus
        EventBus, BridgeWatcher, MemoryWatcher = _try_import_watchers()
        self.bus = EventBus() if EventBus else None
        self.bridge_watcher = (
            BridgeWatcher(self.bus, f"ws://{host}:{port}") if (BridgeWatcher and self.bus) else None
        )
        self.memory_watcher = (
            MemoryWatcher(self.memory, self.bus) if (MemoryWatcher and self.memory and self.bus) else None
        )

    # ------------------------------------------------------------------
    # Send / broadcast
    # ------------------------------------------------------------------

    async def send(self, ws, obj: dict):
        try:
            await ws.send(json.dumps(obj))
        except Exception as e:
            log.warning("Send error: %s", e)

    async def broadcast(self, obj: dict, exclude=None):
        for client in list(self.clients):
            if client is not exclude:
                await self.send(client, obj)

    async def broadcast_ai_response(self, agent: str, reply: str, context: str, exclude=None):
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
    # AI routing
    # ------------------------------------------------------------------

    async def _chat_sovereign(self, msg: str, sys_prompt: str, agent: str = "sovereign") -> str:
        """Route to the local sovereign AI bridge — no external SaaS."""
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

    async def ai_chat(self, ws, msg: str, agent: str, context: str, system: str = "", session: str = "default"):
        sys_prompt = system or (
            "You are a sovereign AI assistant running entirely on self-hosted infrastructure. "
            "No data leaves the network. Be precise and production-ready. "
            "Never fabricate data, and cite uncertainty when unsure."
        )

        # Persist user message to memory (best-effort: init if not yet done)
        if self.hydrator:
            try:
                if self.memory:
                    await self.memory.ensure_initialized()
                await self.hydrator.persist_message(session, "user", msg, agent)
            except Exception as e:
                log.debug("Memory persist (user) skipped: %s", e)

        reply = await self._chat_sovereign(msg, sys_prompt, agent)

        # Persist AI reply to memory
        if self.hydrator:
            try:
                await self.hydrator.persist_message(session, "assistant", reply, agent)
            except Exception as e:
                log.debug("Memory persist (assistant) skipped: %s", e)

        log.info("%s response: %s...", agent, reply[:50])

        response_payload = {
            "type": "ai_response",
            "agent": agent,
            "text": reply,
            "context": context,
            "hash": sha256(reply),
            "ts": int(time.time() * 1000),
        }
        await self.send(ws, response_payload)
        await self.broadcast_ai_response(agent, reply, context, exclude=ws)

        # Publish to event bus
        if self.bus:
            await self.bus.publish("ai_response", {
                "agent": agent,
                "text": reply,
                "session": session,
                "context": context,
            })

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    async def _handle_memory_query(self, ws, message: dict) -> None:
        """Handle memory_query messages from clients."""
        if not self.memory:
            await self.send(ws, {"type": "memory_result", "error": "Memory not available"})
            return

        action = message.get("action", "get_history")
        session = message.get("session", "default")

        if action == "get_history":
            history = await self.memory.get_history(session, limit=message.get("limit", 50))
            await self.send(ws, {"type": "memory_result", "action": action, "data": history, "ts": int(time.time() * 1000)})

        elif action == "get":
            key = message.get("key", "")
            value = await self.memory.get(key)
            await self.send(ws, {"type": "memory_result", "action": action, "key": key, "value": value, "ts": int(time.time() * 1000)})

        elif action == "set":
            key = message.get("key", "")
            value = message.get("value")
            if key:
                await self.memory.set(key, value)
                await self.send(ws, {"type": "memory_result", "action": action, "key": key, "ok": True, "ts": int(time.time() * 1000)})

        elif action == "hydrate":
            if self.hydrator:
                payload = await self.hydrator.hydrate(session)
                await self.send(ws, payload)
            else:
                await self.send(ws, {"type": "memory_result", "error": "Hydrator not available"})

        elif action == "clear":
            await self.memory.clear_history(session)
            await self.send(ws, {"type": "memory_result", "action": action, "ok": True, "ts": int(time.time() * 1000)})

    async def _handle_token_op(self, ws, message: dict) -> None:
        """Handle token_op messages (set/get/status/delete)."""
        if not self.tokens:
            await self.send(ws, {"type": "token_result", "error": "Token handler not available"})
            return

        action = message.get("action", "status")

        if action == "set":
            provider = message.get("provider", "")
            key = message.get("key", "")
            if provider and key:
                canonical = self.tokens.set(provider, key)
                await self.send(ws, {"type": "token_result", "action": action, "provider": canonical, "ok": True, "ts": int(time.time() * 1000)})
            else:
                await self.send(ws, {"type": "token_result", "error": "provider and key required"})

        elif action == "status":
            await self.send(ws, {"type": "token_result", "action": action, "status": self.tokens.status(), "ts": int(time.time() * 1000)})

        elif action == "delete":
            provider = message.get("provider", "")
            ok = self.tokens.delete(provider)
            await self.send(ws, {"type": "token_result", "action": action, "provider": provider, "ok": ok, "ts": int(time.time() * 1000)})

        elif action == "validate":
            provider = message.get("provider", "")
            valid = self.tokens.validate(provider)
            await self.send(ws, {"type": "token_result", "action": action, "provider": provider, "valid": valid, "ts": int(time.time() * 1000)})

    async def _handle_memory_save(self, ws, message: dict) -> None:
        """Handle legacy memory_save messages from PiperTTS.ws (SGHv119.html)."""
        title = message.get("title", "")
        content = message.get("content", "")
        role = message.get("role", "")
        user = message.get("user", "")
        card_id = sha256(f"{title}{content}{int(time.time())}")

        if self.memory and title:
            try:
                await self.memory.set(f"card:{card_id}", {"id": card_id, "title": title, "content": content, "role": role, "user": user, "ts": int(time.time() * 1000)})
            except Exception as e:
                log.debug("memory_save store error for card %s (%s): %s", card_id[:8], title, e)

        await self.send(ws, {"type": "memory_saved", "id": card_id, "label": title, "ts": int(time.time() * 1000)})

    async def _handle_memory_get(self, ws, message: dict) -> None:
        """Handle legacy memory_get messages from PiperTTS.ws (SGHv119.html)."""
        cards: list = []
        if self.memory:
            try:
                # Return recent history entries as card-like objects
                session = message.get("session", "default")
                history = await self.memory.get_history(session, limit=20)
                cards = [
                    {"title": (h.get("role") or "unknown") + " message", "content": h.get("content", ""), "ts": h.get("ts", 0)}
                    for h in (history or [])
                ]
            except Exception as e:
                log.debug("memory_get error: %s", e)
        await self.send(ws, {"type": "memory_result", "cards": cards, "ts": int(time.time() * 1000)})

    async def _handle_ai_code_review(self, ws, message: dict) -> None:
        """Handle ai_code_review messages — review code via sovereign bridge."""
        lang = message.get("lang", "unknown")
        code = message.get("code", "")
        prompt = message.get("prompt") or f"Review this {lang} code. List errors with line numbers. For each error provide an exact fix. Be concise."

        full_prompt = f"{prompt}\n\n```{lang}\n{code}\n```"
        try:
            # sys_prompt is empty because the full prompt is in full_prompt
            review = await self._chat_sovereign(full_prompt, "", agent="code_review")
        except Exception as e:
            review = f"[Code review error: {e}]"

        await self.send(ws, {
            "type": "ai_code_review_result",
            "lang": lang,
            "review": review,
            "ts": int(time.time() * 1000),
        })

    # ------------------------------------------------------------------
    # Client handler
    # ------------------------------------------------------------------

    async def handle_client(self, ws):
        self.clients.add(ws)
        addr = ws.remote_address
        log.info("Client connected: %s | total=%s", addr, len(self.clients))

        # Send handshake with memory hydration on connect
        handshake: dict = {
            "type": "handshake_ack",
            "port": self.port,
            "clients": len(self.clients),
            "memory": self.memory is not None,
            "tokens": self.tokens is not None,
            "ts": int(time.time() * 1000),
        }
        if self.hydrator:
            try:
                handshake["hydration"] = await self.hydrator.hydrate()
            except Exception as e:
                log.warning("Hydration error on connect: %s", e)
        await self.send(ws, handshake)

        try:
            async for raw in ws:
                try:
                    message = json.loads(raw)
                except Exception:
                    continue

                mtype = message.get("type", "")

                if mtype == "ai_chat":
                    agent = message.get("agent", "claude")
                    msg = message.get("message", "")
                    context = message.get("context", "")
                    system = message.get("system", "")
                    session = message.get("session", "default")
                    asyncio.create_task(self.ai_chat(ws, msg, agent, context, system, session))

                elif mtype == "memory_query":
                    asyncio.create_task(self._handle_memory_query(ws, message))

                elif mtype == "memory_save":
                    # Legacy API used by PiperTTS.ws in SGHv119.html
                    asyncio.create_task(self._handle_memory_save(ws, message))

                elif mtype == "memory_get":
                    # Legacy API: retrieve stored memory cards for a role/user
                    asyncio.create_task(self._handle_memory_get(ws, message))

                elif mtype == "ai_code_review":
                    asyncio.create_task(self._handle_ai_code_review(ws, message))

                elif mtype == "token_op":
                    asyncio.create_task(self._handle_token_op(ws, message))

                elif mtype == "ping":
                    await self.send(ws, {"type": "pong", "ts": int(time.time() * 1000)})

                elif mtype == "status":
                    status: dict = {
                        "type": "status_response",
                        "port": self.port,
                        "clients": len(self.clients),
                        "memory": self.memory is not None,
                        "tokens": self.tokens.status() if self.tokens else None,
                        "bus": self.bus.status() if self.bus else None,
                        "bridge_watcher": self.bridge_watcher.status() if self.bridge_watcher else None,
                        "ts": int(time.time() * 1000),
                    }
                    await self.send(ws, status)

                elif mtype == "event_publish":
                    if self.bus:
                        event_type = message.get("event_type", "custom")
                        payload = message.get("payload", {})
                        await self.bus.publish(event_type, payload)

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

    async def start(self):
        if not WS_OK:
            log.error("FATAL: websockets is not installed.")
            sys.exit(1)

        # Initialise memory
        if self.memory:
            try:
                await self.memory.init()
                log.info("Memory store initialised")
            except Exception as e:
                log.warning("Memory init failed: %s", e)

        # Start background watchers
        if self.memory_watcher:
            await self.memory_watcher.start()
        # Note: bridge_watcher monitors external connectivity; skip here to avoid self-loop

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
        await asyncio.Future()  # intentional: keep server alive until cancellation/interruption

    async def stop(self):
        log.info("Stopping BridgeServer...")
        self._stopping = True

        # Stop watchers
        if self.memory_watcher:
            await self.memory_watcher.stop()
        if self.bridge_watcher:
            await self.bridge_watcher.stop()

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

