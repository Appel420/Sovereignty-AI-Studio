"""Twitch chat connector.

Required environment variables:
- TWITCH_CLIENT_ID
- TWITCH_CLIENT_SECRET
- TWITCH_CHANNEL  (channel name to join, e.g. ``appel420``)
"""

import asyncio
import logging
import os
from typing import AsyncIterator, Optional

from platform_connectors.base import PlatformConnector

logger = logging.getLogger(__name__)

PLATFORM = "twitch"


class TwitchConnector(PlatformConnector):
    """Connects to Twitch IRC and relays chat messages."""

    def __init__(self) -> None:
        self._channel = os.getenv("TWITCH_CHANNEL", "")
        self._client_id = os.getenv("TWITCH_CLIENT_ID", "")
        self._client_secret = os.getenv("TWITCH_CLIENT_SECRET", "")
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False

    async def connect(self) -> None:
        """Open an anonymous IRC connection to Twitch."""
        if not self._channel:
            raise ValueError("TWITCH_CHANNEL environment variable not set")
        try:
            self._reader, self._writer = await asyncio.open_connection(
                "irc.chat.twitch.tv", 6667
            )
            self._writer.write(
                b"NICK justinfan12345\r\n"
                b"USER justinfan12345 0 * :Sovereignty\r\n"
            )
            self._writer.write(
                f"JOIN #{self._channel}\r\n".encode()
            )
            await self._writer.drain()
            self._connected = True
            logger.info("Twitch connector joined #%s", self._channel)
        except Exception as exc:
            logger.error("Twitch connect failed: %s", exc)
            raise

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._connected = False
        logger.info("Twitch connector disconnected")

    async def read_chat(self) -> AsyncIterator[dict]:
        if not self._reader:
            return
        while self._connected:
            try:
                line = await asyncio.wait_for(
                    self._reader.readline(), timeout=30
                )
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                # Handle PING keepalive
                if text.startswith("PING"):
                    if self._writer:
                        self._writer.write(b"PONG :tmi.twitch.tv\r\n")
                        await self._writer.drain()
                    continue
                # Parse PRIVMSG
                if "PRIVMSG" in text:
                    user = text.split("!")[0].lstrip(":")
                    msg = text.split("PRIVMSG")[1].split(":", 1)[-1]
                    yield {"user": user, "text": msg, "platform": PLATFORM}
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Twitch read error: %s", exc)
                break

    async def send_message(
        self, text: str, channel: Optional[str] = None
    ) -> None:
        ch = channel or self._channel
        if not self._writer or not ch:
            logger.warning("Twitch: not connected or no channel set")
            return
        self._writer.write(f"PRIVMSG #{ch} :{text}\r\n".encode())
        await self._writer.drain()
