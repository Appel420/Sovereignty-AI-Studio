#!/usr/bin/env python3
"""
Event Bus for Sovereign AI - Redis-backed pub/sub
"""

import asyncio
import logging
import os
from typing import Optional, Callable, Any

# ====================== MODULE LEVEL SETUP ======================
logger = logging.getLogger(__name__)
_REDIS_URL = os.getenv("REDIS_URL")
_redis_client = None


async def _get_redis():
    """Return a redis.asyncio client, creating it on first call."""
    global _redis_client
    if _redis_client is None and _REDIS_URL:
        try:
            import redis.asyncio as aioredis
            _redis_client = await aioredis.from_url(_REDIS_URL)
            logger.info("Event bus connected to Redis at %s", _REDIS_URL)
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            _redis_client = None
    return _redis_client


async def publish(channel: str, message: str):
    """Publish a message to a Redis channel."""
    client = await _get_redis()
    if client:
        await client.publish(channel, message)


async def subscribe(channel: str, callback: Callable[[str], Any]):
    """Subscribe to a Redis channel and call callback on messages."""
    client = await _get_redis()
    if not client:
        return
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    async for message in pubsub.listen():
        if message['type'] == 'message':
            await callback(message['data'].decode())
