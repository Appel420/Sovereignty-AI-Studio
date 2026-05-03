#!/usr/bin/env python3
"""
Sovereignty AI Studio — Bridge Server (ws://localhost:9897)
BridgeServer class-based architecture with:
- Sovereign AI routing (no external SaaS, no Anthropic/OpenAI calls)
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


class BridgeServer:
    """Encapsulates WebSocket server, client handling, AI routing, and broadcast."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.clients: set = set()
        self._server = None
        self._stopping = False

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

    async def ai_chat(self, ws, msg: str, agent: str, context: str, system: str = ""):
        sys_prompt = system or (
            "You are a sovereign AI assistant running entirely on self-hosted infrastructure. "
            "No data leaves the network. Be precise and production-ready. "
            "Never fabricate data, and cite uncertainty when unsure."
        )

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

    async def handle_client(self, ws):
        self.clients.add(ws)
        addr = ws.remote_address
        log.info("Client connected: %s | total=%s", addr, len(self.clients))
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
                    asyncio.create_task(self.ai_chat(ws, msg, agent, context, system))
                else:
                    log.debug("Unhandled message type: %s", mtype)
        except Exception as e:
            log.warning("Client %s error: %s", addr, e)
        finally:
            self.clients.discard(ws)
            log.info("Client disconnected: %s | total=%s", addr, len(self.clients))

    async def start(self):
        if not WS_OK:
            log.error("FATAL: websockets is not installed.")
            sys.exit(1)

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
