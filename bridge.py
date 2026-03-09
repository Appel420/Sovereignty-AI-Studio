#!/usr/bin/env python3
"""
SuperGrok Bridge Server — localhost:9898
BridgeServer class-based architecture with:
- broadcast_ai_response helper
- graceful shutdown via stop()
- AI agent calls refactored into _chat_claude, _chat_gpt, _chat_grok
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

try:
    import anthropic

    CLAUDE_OK = True
except ImportError:
    CLAUDE_OK = False

try:
    import openai

    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

PORT = int(os.environ.get("SG_PORT", 9898))
HOST = os.environ.get("SG_HOST", "localhost")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GROK_KEY = os.environ.get("GROK_API_KEY", "")
COPILOT_TOKEN = os.environ.get("GITHUB_COPILOT_TOKEN", "")

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

    async def _chat_claude(self, msg: str, sys_prompt: str) -> str:
        try:
            client = anthropic.Anthropic(api_key=CLAUDE_KEY)
            result = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2048,
                system=sys_prompt,
                messages=[{"role": "user", "content": msg}],
            )
            return result.content[0].text if result.content else ""
        except Exception as e:
            log.error("Claude error: %s", e)
            return f"[Claude error: {e}]"

    async def _chat_gpt(self, msg: str, sys_prompt: str) -> str:
        try:
            client = openai.OpenAI(api_key=OPENAI_KEY)
            result = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": msg},
                ],
            )
            return result.choices[0].message.content or ""
        except Exception as e:
            log.error("GPT error: %s", e)
            return f"[GPT-4o error: {e}]"

    async def _chat_grok(self, msg: str, sys_prompt: str) -> str:
        try:
            req = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=json.dumps(
                    {
                        "model": "grok-3",
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": msg},
                        ],
                        "max_tokens": 2048,
                    }
                ).encode(),
                headers={
                    "Authorization": f"Bearer {GROK_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            log.error("Grok error: %s", e)
            return f"[Grok error: {e}]"

    async def ai_chat(self, ws, msg: str, agent: str, context: str, system: str = ""):
        sys_prompt = system or (
            "You are a highly capable AI assistant integrated into SuperGrok — "
            "a secure, on-device AI platform. Be precise and production-ready. "
            "Never fabricate data, and cite uncertainty when unsure."
        )

        reply = ""
        agent_lower = agent.lower()

        if agent_lower in ("claude", "claude_sonnet", "") and CLAUDE_OK and CLAUDE_KEY:
            reply = await self._chat_claude(msg, sys_prompt)
        elif agent_lower in ("gpt", "gpt-4o", "openai") and OPENAI_OK and OPENAI_KEY:
            reply = await self._chat_gpt(msg, sys_prompt)
        elif agent_lower in ("grok", "grok4.20", "xai") and GROK_KEY:
            reply = await self._chat_grok(msg, sys_prompt)
        else:
            keys = {
                "claude": "ANTHROPIC_API_KEY",
                "gpt": "OPENAI_API_KEY",
                "grok": "GROK_API_KEY",
                "copilot": "GITHUB_COPILOT_TOKEN",
            }
            reply = f"[{agent} offline — set {keys.get(agent_lower, 'API_KEY')} before starting bridge.py]"

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
        await asyncio.Future()

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


if __name__ == "__main__":
    server = BridgeServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        asyncio.run(server.stop())
        print("\nBridge stopped.")
