"""X (formerly Twitter) connector — streams mentions and DMs.

Required environment variables:
- X_BEARER_TOKEN — X API v2 bearer token
- X_LISTEN_QUERY — Search query for filtered stream (default: ``sovereignty``)
"""

import asyncio
import logging
import os
from typing import AsyncIterator, Optional

import httpx

from platform_connectors.base import PlatformConnector

logger = logging.getLogger(__name__)

PLATFORM = "x"
_API_BASE = "https://api.twitter.com/2"


class XConnector(PlatformConnector):
    """Streams X (Twitter) tweets matching a configured query."""

    def __init__(self) -> None:
        self._bearer_token = os.getenv("X_BEARER_TOKEN", "")
        self._query = os.getenv("X_LISTEN_QUERY", "sovereignty")
        self._connected = False
        self._stream_resp: Optional[httpx.Response] = None
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._bearer_token}"}

    async def connect(self) -> None:
        if not self._bearer_token:
            raise ValueError("X_BEARER_TOKEN environment variable not set")
        # Add a stream rule for our query
        self._client = httpx.AsyncClient(timeout=None)
        rules_resp = await self._client.post(
            f"{_API_BASE}/tweets/search/stream/rules",
            headers=self._headers(),
            json={
                "add": [{"value": self._query, "tag": "sovereignty_query"}]
            },
        )
        if rules_resp.status_code not in (200, 201):
            logger.warning(
                "X: Could not add stream rule: %s", rules_resp.text
            )
        self._connected = True
        logger.info("X connector ready, query: '%s'", self._query)

    async def disconnect(self) -> None:
        if self._stream_resp:
            await self._stream_resp.aclose()
        if self._client:
            await self._client.aclose()
        self._connected = False
        logger.info("X connector disconnected")

    async def read_chat(self) -> AsyncIterator[dict]:
        if not self._client:
            return
        try:
            async with self._client.stream(
                "GET",
                f"{_API_BASE}/tweets/search/stream",
                headers=self._headers(),
                params={"tweet.fields": "author_id,text"},
            ) as resp:
                self._stream_resp = resp
                async for line in resp.aiter_lines():
                    if not self._connected:
                        break
                    if not line.strip():
                        continue
                    try:
                        import json
                        data = json.loads(line)
                        tweet = data.get("data", {})
                        yield {
                            "user": tweet.get("author_id", "unknown"),
                            "text": tweet.get("text", ""),
                            "platform": PLATFORM,
                        }
                    except Exception as exc:
                        logger.warning("X parse error: %s", exc)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("X stream error: %s", exc)

    async def send_message(
        self, text: str, channel: Optional[str] = None
    ) -> None:
        """Post a tweet reply."""
        if not self._client:
            logger.warning("X: not connected")
            return
        try:
            payload: dict = {"text": text}
            if channel:
                payload["reply"] = {"in_reply_to_tweet_id": channel}
            resp = await self._client.post(
                f"{_API_BASE}/tweets",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            logger.info("X: posted tweet")
        except Exception as exc:
            logger.error("X send_message failed: %s", exc)
