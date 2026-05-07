"""Kick.com chat connector (WebSocket-based).

Required environment variables:
- KICK_CLIENT_ID      — Kick OAuth application client ID
- KICK_CHANNEL        — Channel name to connect to
"""

import asyncio
import json
import logging
import os
from typing import AsyncIterator, Optional

from platform_connectors.base import PlatformConnector

logger = logging.getLogger(__name__)

PLATFORM = "kick"
_WS_URL = "wss://ws-us2.pusher.com/app/eb1d5f98991a78b932c"


class KickConnector(PlatformConnector):
    """Connects to Kick's Pusher-based WebSocket and reads chat."""

    def __init__(self) -> None:
        self._channel_name = os.getenv("KICK_CHANNEL", "")
        self._client_id = os.getenv("KICK_CLIENT_ID", "")
        self._ws = None
        self._connected = False

    async def connect(self) -> None:
        if not self._channel_name:
            raise ValueError("KICK_CHANNEL environment variable not set")
        try:
            import websockets  # type: ignore

            self._ws = await websockets.connect(
                f"{_WS_URL}?protocol=7&client=js&version=7.6.0&flash=false"
            )
            # Subscribe to the channel's chat room
            subscribe_msg = json.dumps(
                {
                    "event": "pusher:subscribe",
                    "data": {
                        "channel": f"chatrooms.{self._channel_name}.v2"
                    },
                }
            )
            await self._ws.send(subscribe_msg)
            self._connected = True
            logger.info("Kick connector subscribed to %s", self._channel_name)
        except ImportError:
            raise RuntimeError(
                "websockets package required for Kick connector"
            )
        except Exception as exc:
            logger.error("Kick connect failed: %s", exc)
            raise

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()
        self._connected = False
        logger.info("Kick connector disconnected")

    async def read_chat(self) -> AsyncIterator[dict]:
        if not self._ws:
            return
        while self._connected:
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=30)
                data = json.loads(raw)
                event = data.get("event", "")
                if event == "App\\Events\\ChatMessageEvent":
                    payload = json.loads(data.get("data", "{}"))
                    sender = payload.get("sender", {})
                    yield {
                        "user": sender.get("username", "unknown"),
                        "text": payload.get("content", ""),
                        "platform": PLATFORM,
                    }
                elif event == "pusher:ping":
                    await self._ws.send(json.dumps({"event": "pusher:pong"}))
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Kick read error: %s", exc)
                break

    async def send_message(
        self, text: str, channel: Optional[str] = None
    ) -> None:
        logger.warning("Kick: send_message requires authenticated API access")
