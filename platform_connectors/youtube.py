"""YouTube Live Chat connector.

Required environment variables:
- YOUTUBE_API_KEY     — Google API key with YouTube Data API v3 enabled
- YOUTUBE_STREAM_ID   — Live broadcast / video ID
"""

import asyncio
import logging
import os
from typing import AsyncIterator, Optional

import httpx

from platform_connectors.base import PlatformConnector

logger = logging.getLogger(__name__)

PLATFORM = "youtube"
_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeConnector(PlatformConnector):
    """Polls the YouTube Live Chat API and relays messages."""

    def __init__(self) -> None:
        self._api_key = os.getenv("YOUTUBE_API_KEY", "")
        self._video_id = os.getenv("YOUTUBE_STREAM_ID", "")
        self._live_chat_id: Optional[str] = None
        self._connected = False
        self._poll_interval = 5  # seconds

    async def connect(self) -> None:
        """Resolve the live chat ID for the configured video/broadcast."""
        if not self._api_key or not self._video_id:
            raise ValueError(
                "YOUTUBE_API_KEY and YOUTUBE_STREAM_ID must be set"
            )
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{_API_BASE}/videos",
                params={
                    "part": "liveStreamingDetails",
                    "id": self._video_id,
                    "key": self._api_key,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                raise ValueError(f"No YouTube video found for ID {self._video_id}")
            self._live_chat_id = (
                items[0]
                .get("liveStreamingDetails", {})
                .get("activeLiveChatId")
            )
            if not self._live_chat_id:
                raise ValueError("No active live chat found for this video")
        self._connected = True
        logger.info("YouTube connector ready, chat ID: %s", self._live_chat_id)

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("YouTube connector disconnected")

    async def read_chat(self) -> AsyncIterator[dict]:
        if not self._live_chat_id:
            return
        page_token: Optional[str] = None
        async with httpx.AsyncClient(timeout=10) as client:
            while self._connected:
                try:
                    params = {
                        "part": "snippet,authorDetails",
                        "liveChatId": self._live_chat_id,
                        "key": self._api_key,
                    }
                    if page_token:
                        params["pageToken"] = page_token
                    resp = await client.get(
                        f"{_API_BASE}/liveChat/messages", params=params
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    page_token = data.get("nextPageToken")
                    poll_ms = data.get("pollingIntervalMillis", 5000)
                    for item in data.get("items", []):
                        author = item.get("authorDetails", {}).get(
                            "displayName", "unknown"
                        )
                        text = (
                            item.get("snippet", {})
                            .get("displayMessage", "")
                        )
                        yield {
                            "user": author,
                            "text": text,
                            "platform": PLATFORM,
                        }
                    await asyncio.sleep(poll_ms / 1000)
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.warning("YouTube read error: %s", exc)
                    await asyncio.sleep(self._poll_interval)

    async def send_message(
        self, text: str, channel: Optional[str] = None
    ) -> None:
        logger.warning(
            "YouTube: send_message requires OAuth2; read-only mode active"
        )
