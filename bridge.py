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
    from websockets.asyncio.server import serve
except ImportError:
    try:
        from websockets.server import serve
    except ImportError:
        serve = None

if serve is None:
    WS_OK = False
    print("WARNING: websockets not installed. Run: pip3 install websockets")
else:
    WS_OK = True

PORT = int(os.environ.get("SG_PORT", 9897))
HOST = os.environ.get("SG_HOST", "127.0.0.1")
SOVEREIGN_API_URL = os.environ.get(
    "SOVEREIGN_API_URL", "http://127.0.0.1:9897/api/ai"
).rstrip("/")

ROOT_DIR = pathlib.Path(__file__).parent
# Compatibility namespace: keep the documented root bridge.py launcher while
# allowing bridge.local_dashboard_status and bridge.serve_dashboard imports.
_PACKAGE_DIR = ROOT_DIR / "bridge"
if _PACKAGE_DIR.is_dir():
    __path__ = [str(_PACKAGE_DIR)]

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
    """Encapsulates WebSocket server, clients, routing, and local state."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.clients: set = set()
        self._server = None
        self._stopping = False

        MemoryStore, MemoryHydrator = _try_import_memory()
        self.memory = MemoryStore() if MemoryStore else None
        self.hydrator = MemoryHydrator(self.memory) if (MemoryHydrator and self.memory) else None

        TokenManager = _try_import_token_handler()
        self.tokens = TokenManager() if TokenManager else None
        if self.tokens:
            self.tokens.import_from_env(os.environ)

        EventBus, BridgeWatcher, MemoryWatcher = _try_import_watchers()
        self.bus = EventBus() if EventBus else None
        self.bridge_watcher = (
            BridgeWatcher(self.bus, f"ws://{host}:{port}") if (BridgeWatcher and self.bus) else None
        )
        self.memory_watcher = (
            MemoryWatcher(self.memory, self.bus) if (MemoryWatcher and self.memory and self.bus) else None
        )

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
        await self.broadcast({
            "type": "ai_response", "agent": agent, "text": reply,
            "context": context, "hash": sha256(reply), "ts": int(time.time() * 1000),
        }, exclude=exclude)

    async def _chat_sovereign(self, msg: str, sys_prompt: str, agent: str = "sovereign") -> str:
        try:
            from ai_core.sovereign_bridge import SovereignBridge
            bridge = SovereignBridge()
            messages = ([{"role": "system", "content": sys_prompt}] if sys_prompt else [])
            messages.append({"role": "user", "content": msg})
            return bridge.chat(messages)
        except Exception as e:
            log.warning("Sovereign bridge unavailable: %s", e)
            return f"[Sovereign bridge unavailable: {e}]"

    async def handle_client(self, ws):
        self.clients.add(ws)
        try:
            await self.send(ws, {
                "type": "handshake_ack", "port": self.port,
                "clients": len(self.clients), "memory": self.memory is not None,
                "tokens": self.tokens is not None, "ts": int(time.time() * 1000),
            })
            async for raw in ws:
                try:
                    message = json.loads(raw)
                except Exception:
                    continue
                mtype = message.get("type", "")
                if mtype == "ping":
                    await self.send(ws, {"type": "pong", "ts": int(time.time() * 1000)})
                elif mtype == "status":
                    await self.send(ws, {
                        "type": "status_response", "port": self.port,
                        "clients": len(self.clients), "memory": self.memory is not None,
                        "tokens": self.tokens.status() if self.tokens else None,
                        "ts": int(time.time() * 1000),
                    })
                elif mtype == "ai_chat":
                    reply = await self._chat_sovereign(
                        message.get("message", ""), message.get("system", ""), message.get("agent", "sovereign")
                    )
                    await self.send(ws, {
                        "type": "ai_response", "agent": message.get("agent", "sovereign"),
                        "text": reply, "context": message.get("context", ""),
                        "hash": sha256(reply), "ts": int(time.time() * 1000),
                    })
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            log.warning("Client error: %s", e)
        finally:
            self.clients.discard(ws)

    async def start(self):
        if not WS_OK:
            raise RuntimeError("websockets is not installed")
        log.info("Bridge starting on ws://%s:%s", self.host, self.port)
        self._server = await serve(self.handle_client, self.host, self.port)
        await asyncio.Future()

    async def stop(self):
        self._stopping = True
        for client in list(self.clients):
            await client.close()
        self.clients.clear()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()


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
