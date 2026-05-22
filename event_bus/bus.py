#!/usr/bin/env python3
"""Async event bus for inter-agent communication."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import defaultdict
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "")
_redis_client: Optional[Any] = None

_local_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
_subscriptions: dict[str, list[Callable[[Any], Any]]] = defaultdict(list)


async def _get_redis():
    """Return a redis.asyncio client, creating it on first call."""
    global _redis_client
    if _redis_client is None and _REDIS_URL:
        try:
            import redis.asyncio as aioredis

            _redis_client = aioredis.from_url(_REDIS_URL)
            logger.info("Event bus connected to Redis at %s", _REDIS_URL)
        except Exception as exc:  # pragma: no cover - depends on environment
            logger.warning("Redis unavailable (%s); using in-process queue", exc)
            _redis_client = None
    return _redis_client


async def publish(channel: str, message: Any) -> None:
    """Publish a message to a channel."""
    client = await _get_redis()
    if client:
        await client.publish(channel, json.dumps(message))
        return

    for callback in list(_subscriptions.get(channel, [])):
        result = callback(message)
        if asyncio.iscoroutine(result):
            await result


async def subscribe(channel: str, callback: Callable[[Any], Any]) -> None:
    """Subscribe a callback to a channel."""
    _subscriptions[channel].append(callback)

    client = await _get_redis()
    if not client:
        return

    pubsub = client.pubsub()
    await pubsub.subscribe(channel)

    async def _pump() -> None:
        async for raw in pubsub.listen():
            if raw.get("type") != "message":
                continue
            payload = raw.get("data")
            if isinstance(payload, (bytes, bytearray)):
                payload = payload.decode()
            try:
                payload = json.loads(payload)
            except Exception:
                pass
            result = callback(payload)
            if asyncio.iscoroutine(result):
                await result

    asyncio.create_task(_pump())


def register_handler(agent_id: str, handler: Callable[[dict[str, Any]], Any]) -> None:
    """Register a coroutine handler for queued agent events."""
    _handlers[agent_id] = handler
    logger.info("Registered handler for agent '%s'", agent_id)


async def send_event(agent_id: str, task: dict[str, Any]) -> None:
    """Enqueue a task for an agent."""
    event = {"agent_id": agent_id, "task": task}
    client = await _get_redis()
    if client:
        try:
            await client.lpush("sg:events", json.dumps(event))
            logger.debug("Sent Redis event to %s: %s", agent_id, task)
            return
        except Exception as exc:  # pragma: no cover - depends on Redis
            logger.warning("Redis send failed (%s); falling back to queue", exc)

    await _local_queue.put(event)
    logger.debug("Sent local event to %s: %s", agent_id, task)


async def process_events() -> None:
    """Continuously dequeue and dispatch events to registered handlers."""
    logger.info("Event bus processing loop started")
    client = await _get_redis()

    while True:
        try:
            if client:
                raw = await client.brpop("sg:events", timeout=1)
                if raw is None:
                    continue
                event = json.loads(raw[1])
            else:
                event = await asyncio.wait_for(_local_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            logger.info("Event bus processing loop cancelled")
            raise

        agent_id = event.get("agent_id", "")
        task = event.get("task", {})
        handler = _handlers.get(agent_id)
        if handler is None:
            logger.warning("No handler for agent '%s'; dropping event", agent_id)
            continue

        try:
            result = handler(task)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # pragma: no cover - handler specific
            logger.error(
                "Handler for '%s' raised an error: %s",
                agent_id,
                exc,
                exc_info=True,
            )
