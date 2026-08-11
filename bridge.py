#!/usr/bin/env python3
"""Sovereignty AI Studio local WebSocket bridge."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import pathlib
import sys
import time
from typing import Any

try:
    from websockets.asyncio.server import serve
except ImportError:
    try:
        from websockets.server import serve
    except ImportError:
        serve = None

WS_OK = serve is not None
PORT = int(os.environ.get("SG_PORT", "9897"))
HOST = os.environ.get("SG_HOST", "127.0.0.1")
SOVEREIGN_API_URL = os.environ.get(
    "SOVEREIGN_API_URL", "http://127.0.0.1:9897/api/ai"
).rstrip("/")

ROOT_DIR = pathlib.Path(__file__).parent
_PACKAGE_DIR = ROOT_DIR / "bridge"
if _PACKAGE_DIR.is_dir():
    # Keep the root bridge.py launcher compatible with bridge.* submodule imports.
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
    except ImportError as exc:
        log.warning("memory module not available: %s", exc)
        return None, None


def _try_import_token_handler():
    try:
        from token_handler.manager import TokenManager
        return TokenManager
    except ImportError as exc:
        log.warning("token_handler module not available: %s", exc)
        return None


def _try_import_watchers():
    try:
        from watchers.event_bus import EventBus
        from watchers.bridge_watcher import BridgeWatcher
        from watchers.memory_watcher import MemoryWatcher
        return EventBus, BridgeWatcher, MemoryWatcher
    except ImportError as exc:
        log.warning("watchers module not available: %s", exc)
        return None, None, None


class BridgeServer:
    """Local WebSocket bridge with optional memory, tokens, and watchers."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.clients: set[Any] = set()
        self._server = None
        self._stopping = False

        MemoryStore, MemoryHydrator = _try_import_memory()
        self.memory = MemoryStore() if MemoryStore else None
        self.hydrator = (
            MemoryHydrator(self.memory)
            if MemoryHydrator and self.memory
            else None
        )

        TokenManager = _try_import_token_handler()
        self.tokens = TokenManager() if TokenManager else None
        if self.tokens:
            self.tokens.import_from_env(os.environ)

        EventBus, BridgeWatcher, MemoryWatcher = _try_import_watchers()
        self.bus = EventBus() if EventBus else None
        self.bridge_watcher = (
            BridgeWatcher(self.bus, f"ws://{host}:{port}")
            if BridgeWatcher and self.bus
            else None
        )
        self.memory_watcher = (
            MemoryWatcher(self.memory, self.bus)
            if MemoryWatcher and self.memory and self.bus
            else None
        )

    async def send(self, ws, payload: dict) -> None:
        try:
            await ws.send(json.dumps(payload))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            log.warning("Send error: %s", exc)

    async def broadcast(self, payload: dict, exclude=None) -> None:
        for client in list(self.clients):
            if client is not exclude:
                await self.send(client, payload)

    async def _chat_sovereign(
        self, message: str, system: str = "", agent: str = "sovereign"
    ) -> str:
        try:
            from ai_core.sovereign_bridge import SovereignBridge

            messages = ([{"role": "system", "content": system}] if system else [])
            messages.append({"role": "user", "content": message})
            return SovereignBridge().chat(messages)
        except Exception as exc:  # noqa: BLE001
            log.warning("Sovereign bridge unavailable: %s", exc)
            return f"[Sovereign bridge unavailable: {exc}]"

    async def _ai_chat(self, ws, message: dict) -> None:
        agent = message.get("agent", "sovereign")
        reply = await self._chat_sovereign(
            message.get("message", ""), message.get("system", ""), agent
        )
        payload = {
            "type": "ai_response",
            "agent": agent,
            "text": reply,
            "context": message.get("context", ""),
            "hash": sha256(reply),
            "ts": int(time.time() * 1000),
        }
        await self.send(ws, payload)
        await self.broadcast(payload, exclude=ws)

    async def _memory_query(self, ws, message: dict) -> None:
        if not self.memory:
            await self.send(ws, {"type": "memory_result", "error": "Memory not available"})
            return
        action = message.get("action", "get_history")
        session = message.get("session", "default")
        if action == "get_history":
            data = await self.memory.get_history(session, limit=message.get("limit", 50))
            await self.send(ws, {"type": "memory_result", "action": action, "data": data})
        elif action == "get":
            key = message.get("key", "")
            await self.send(ws, {"type": "memory_result", "action": action, "key": key, "value": await self.memory.get(key)})
        elif action == "set" and message.get("key"):
            key = message["key"]
            await self.memory.set(key, message.get("value"))
            await self.send(ws, {"type": "memory_result", "action": action, "key": key, "ok": True})
        elif action == "hydrate" and self.hydrator:
            await self.send(ws, await self.hydrator.hydrate(session))
        elif action == "clear":
            await self.memory.clear_history(session)
            await self.send(ws, {"type": "memory_result", "action": action, "ok": True})

    async def handle_client(self, ws) -> None:
        self.clients.add(ws)
        try:
            await self.send(ws, {
                "type": "handshake_ack",
                "port": self.port,
                "clients": len(self.clients),
                "memory": self.memory is not None,
                "tokens": self.tokens is not None,
                "ts": int(time.time() * 1000),
            })
            async for raw in ws:
                try:
                    message = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                message_type = message.get("type", "")
                if message_type == "ping":
                    await self.send(ws, {"type": "pong", "ts": int(time.time() * 1000)})
                elif message_type == "status":
                    await self.send(ws, {
                        "type": "status_response",
                        "port": self.port,
                        "clients": len(self.clients),
                        "memory": self.memory is not None,
                        "tokens": self.tokens.status() if self.tokens else None,
                        "bus": self.bus.status() if self.bus else None,
                        "bridge_watcher": self.bridge_watcher.status() if self.bridge_watcher else None,
                        "ts": int(time.time() * 1000),
                    })
                elif message_type == "ai_chat":
                    asyncio.create_task(self._ai_chat(ws, message))
                elif message_type == "memory_query":
                    asyncio.create_task(self._memory_query(ws, message))
                elif message_type == "event_publish" and self.bus:
                    await self.bus.publish(
                        message.get("event_type", "custom"), message.get("payload", {})
                    )
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # noqa: BLE001
            log.warning("Client error: %s", exc)
        finally:
            self.clients.discard(ws)

    async def start(self) -> None:
        if not WS_OK:
            raise RuntimeError("websockets is not installed")
        if self.memory:
            try:
                await self.memory.init()
            except Exception as exc:  # noqa: BLE001
                log.warning("Memory init failed: %s", exc)
        if self.memory_watcher:
            await self.memory_watcher.start()
        self._server = await serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=30,
            max_size=50 * 1024 * 1024,
        )
        log.info("Bridge LIVE → ws://%s:%s", self.host, self.port)
        await asyncio.Future()

    async def stop(self) -> None:
        self._stopping = True
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


async def _main() -> None:
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
