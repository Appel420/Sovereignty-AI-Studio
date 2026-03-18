"""Platform Agent — manages streaming platform connections.

Connects to one or more streaming platforms (Twitch, YouTube, Kick, X) and
routes incoming chat messages to the event bus.  All connections are managed
under Judge supervision.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from platform_connectors.base import PlatformConnector

logger = logging.getLogger(__name__)


def _build_connectors() -> Dict[str, PlatformConnector]:
    """Build connector instances based on available environment variables."""
    connectors: Dict[str, PlatformConnector] = {}

    if os.getenv("TWITCH_CHANNEL"):
        try:
            from platform_connectors.twitch import TwitchConnector
            connectors["twitch"] = TwitchConnector()
        except Exception as exc:
            logger.warning("Twitch connector unavailable: %s", exc)

    if os.getenv("YOUTUBE_STREAM_ID") and os.getenv("YOUTUBE_API_KEY"):
        try:
            from platform_connectors.youtube import YouTubeConnector
            connectors["youtube"] = YouTubeConnector()
        except Exception as exc:
            logger.warning("YouTube connector unavailable: %s", exc)

    if os.getenv("KICK_CHANNEL"):
        try:
            from platform_connectors.kick import KickConnector
            connectors["kick"] = KickConnector()
        except Exception as exc:
            logger.warning("Kick connector unavailable: %s", exc)

    if os.getenv("X_BEARER_TOKEN"):
        try:
            from platform_connectors.x_connector import XConnector
            connectors["x"] = XConnector()
        except Exception as exc:
            logger.warning("X connector unavailable: %s", exc)

    return connectors


class PlatformAgent:
    """Manages multiple platform connectors under Judge supervision."""

    AGENT_ID = "platform_agent"

    def __init__(self, judge: Any) -> None:
        self._judge = judge
        self._connectors: Dict[str, PlatformConnector] = {}
        self._tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Connect to all configured platforms and begin listening."""
        self._connectors = _build_connectors()
        if not self._connectors:
            logger.info("PlatformAgent: no platforms configured")
            return

        for name, connector in self._connectors.items():
            task = {
                "resource": f"platform:{name}",
                "action": "connect",
            }
            approved, reason = await self._judge.approve_task(
                self.AGENT_ID, task
            )
            if not approved:
                logger.warning(
                    "PlatformAgent: Judge rejected %s connection: %s",
                    name,
                    reason,
                )
                continue
            try:
                await connector.connect()
                t = asyncio.create_task(
                    self._listen(name, connector),
                    name=f"platform-{name}",
                )
                self._tasks.append(t)
                logger.info("PlatformAgent: connected to %s", name)
            except Exception as exc:
                logger.error(
                    "PlatformAgent: failed to connect %s: %s", name, exc
                )
                await self._judge.release_task(
                    self.AGENT_ID, f"platform:{name}"
                )

    async def stop(self) -> None:
        """Disconnect all platforms and cancel listener tasks."""
        for t in self._tasks:
            t.cancel()
        for name, connector in self._connectors.items():
            try:
                await connector.disconnect()
            except Exception as exc:
                logger.warning("PlatformAgent: error disconnecting %s: %s", name, exc)
            await self._judge.release_task(self.AGENT_ID, f"platform:{name}")
        self._tasks.clear()
        logger.info("PlatformAgent: all platforms disconnected")

    async def send_to(
        self, platform: str, text: str, channel: Optional[str] = None
    ) -> None:
        """Send *text* to the specified *platform*."""
        connector = self._connectors.get(platform)
        if connector is None:
            logger.warning("PlatformAgent: unknown platform '%s'", platform)
            return
        await connector.send_message(text, channel)

    async def _listen(
        self, name: str, connector: PlatformConnector
    ) -> None:
        """Read messages from *connector* and log/dispatch them."""
        try:
            async for message in connector.read_chat():
                logger.info(
                    "[%s] %s: %s",
                    name,
                    message.get("user"),
                    message.get("text"),
                )
                # Future: forward to event bus
                # await send_event("chat_processor", message)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("PlatformAgent listener %s crashed: %s", name, exc)
