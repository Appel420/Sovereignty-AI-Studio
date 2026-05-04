"""
event_bus/bus.py
================
Async event bus for inter-agent communication in Sovereignty AI Studio.

Features
--------
- **Typed events** via the :class:`BusEvent` dataclass so callers have a
  clear contract rather than raw dicts.
- **Subscribe / publish** pattern — multiple handlers may subscribe to the
  same ``agent_id``; all are called for each matching event.
- **Async event processing** — all handler calls are non-blocking.
- **Dead-letter queue (DLQ)** — events whose handlers raise after
  ``MAX_HANDLER_RETRIES`` attempts are moved to :data:`dead_letter_queue`
  for inspection / replay instead of being silently dropped.
- **Redis or in-process** — when ``REDIS_URL`` is set events flow through
  a Redis list for cross-process delivery; otherwise a local asyncio.Queue
  is used with no external dependency.

Backward-compatible
-------------------
The module-level ``send_event`` / ``register_handler`` / ``process_events``
functions from the original bus are preserved so existing code keeps working.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_REDIS_URL: str = os.getenv("REDIS_URL", "")
_REDIS_QUEUE_KEY: str = "sg:events"
MAX_HANDLER_RETRIES: int = 3          # attempts before DLQ
RETRY_BASE_DELAY_SECS: float = 0.25  # exponential backoff base

# ---------------------------------------------------------------------------
# Optional Redis client (lazy init)
# ---------------------------------------------------------------------------
_redis_client: Optional[Any] = None


async def _get_redis() -> Optional[Any]:
    """Return a shared aioredis client, creating it on first call.

    Falls back gracefully to ``None`` when Redis is unavailable so the bus
    automatically degrades to in-process mode.
    """
    global _redis_client
    if _redis_client is None and _REDIS_URL:
        try:
            import aioredis  # type: ignore

            _redis_client = await aioredis.from_url(_REDIS_URL)
            logger.info("Event bus connected to Redis at %s", _REDIS_URL)
        except Exception as exc:
            logger.warning("Redis unavailable (%s); using in-process queue", exc)
    return _redis_client


# ---------------------------------------------------------------------------
# Typed event dataclass
# ---------------------------------------------------------------------------
@dataclass
class BusEvent:
    """A typed event envelope routed through the event bus.

    Attributes:
        agent_id:  Target agent / handler identifier (e.g. ``"judge"``).
        task:      Arbitrary task payload dict.
        event_id:  Auto-generated UUID for tracing.
        timestamp: Unix timestamp of event creation.
        attempt:   Current delivery attempt (incremented on retry).
    """

    agent_id: str
    task: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    attempt: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict (JSON-compatible)."""
        return {
            "agent_id": self.agent_id,
            "task": self.task,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "attempt": self.attempt,
        }

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access for backward compatibility (e.g. event["agent_id"])."""
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Allow .get() access for backward compatibility."""
        return self.to_dict().get(key, default)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BusEvent":
        """Deserialise from a plain dict."""
        return cls(
            agent_id=data["agent_id"],
            task=data.get("task", {}),
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            attempt=data.get("attempt", 1),
        )


# ---------------------------------------------------------------------------
# State: handlers, local queue, DLQ
# ---------------------------------------------------------------------------
# Multi-subscriber: agent_id → list of handlers
_handlers: Dict[str, List[Callable]] = {}

# In-process fallback queue (when Redis is not configured)
_local_queue: asyncio.Queue = asyncio.Queue()

# Dead-letter queue: events that could not be delivered after max retries
dead_letter_queue: List[BusEvent] = []

# Maximum DLQ size; oldest entries are pruned when full
_DLQ_MAX_SIZE: int = 500


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def send_event(agent_id: str, task: Dict[str, Any]) -> None:
    """Enqueue a :class:`BusEvent` for *agent_id*.

    Args:
        agent_id: Target agent identifier (e.g. ``"judge"``, ``"ai_router"``).
        task:     Arbitrary task payload dictionary.

    The event is delivered to Redis when ``REDIS_URL`` is configured;
    otherwise it is placed in the in-process local queue.
    """
    event = BusEvent(agent_id=agent_id, task=task)
    redis = await _get_redis()
    if redis:
        try:
            await redis.lpush(_REDIS_QUEUE_KEY, json.dumps(event.to_dict()))
            logger.debug("Bus → Redis: agent='%s' event_id=%s", agent_id, event.event_id)
            return
        except Exception as exc:
            logger.warning("Redis send failed (%s); falling back to local queue", exc)
    await _local_queue.put(event)
    logger.debug("Bus → local: agent='%s' event_id=%s", agent_id, event.event_id)


def register_handler(agent_id: str, handler: Callable) -> None:
    """Register a coroutine *handler* for *agent_id*.

    Multiple handlers may be registered for the same ``agent_id``; all
    will be called for each matching event (fan-out).

    Args:
        agent_id: Target agent identifier.
        handler:  Async (or sync) callable that receives a task dict.
    """
    if agent_id not in _handlers:
        _handlers[agent_id] = []
    _handlers[agent_id].append(handler)
    logger.info("Event bus: registered handler for agent '%s'", agent_id)


def unregister_handler(agent_id: str, handler: Optional[Callable] = None) -> None:
    """Remove a handler registration.

    Args:
        agent_id: Agent whose handler(s) to remove.
        handler:  Specific handler to remove.  When ``None`` all handlers
                  for *agent_id* are removed.
    """
    if agent_id not in _handlers:
        return
    if handler is None:
        del _handlers[agent_id]
        logger.info("Event bus: removed all handlers for agent '%s'", agent_id)
    else:
        _handlers[agent_id] = [h for h in _handlers[agent_id] if h is not handler]
        if not _handlers[agent_id]:
            del _handlers[agent_id]
        logger.debug("Event bus: removed handler for agent '%s'", agent_id)


async def process_events() -> None:
    """Continuously dequeue and dispatch events to registered handlers.

    Runs until the current asyncio task is cancelled.  Events with no
    registered handler are logged as warnings.  Events whose handlers fail
    after ``MAX_HANDLER_RETRIES`` retries are moved to :data:`dead_letter_queue`.
    """
    logger.info("Event bus processing loop started")
    redis = await _get_redis()

    while True:
        # ── Dequeue one event ──────────────────────────────────────────
        try:
            if redis:
                raw = await redis.brpop(_REDIS_QUEUE_KEY, timeout=1)
                if raw is None:
                    continue
                event = BusEvent.from_dict(json.loads(raw[1]))
            else:
                event = await asyncio.wait_for(_local_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            logger.info("Event bus processing loop cancelled")
            raise

        # ── Dispatch ──────────────────────────────────────────────────
        handlers = _handlers.get(event.agent_id)
        if not handlers:
            logger.warning(
                "Event bus: no handler for agent '%s' (event_id=%s) — dropping",
                event.agent_id,
                event.event_id,
            )
            continue

        for handler in handlers:
            await _call_with_retry(handler, event)


async def _call_with_retry(handler: Callable, event: BusEvent) -> None:
    """Invoke *handler* with exponential-backoff retries.

    On exhaustion the event is sent to :data:`dead_letter_queue`.
    """
    for attempt in range(1, MAX_HANDLER_RETRIES + 1):
        try:
            result = handler(event.task)
            if asyncio.iscoroutine(result):
                await result
            return  # Success — stop retrying
        except Exception as exc:
            delay = RETRY_BASE_DELAY_SECS * (2 ** (attempt - 1))
            logger.warning(
                "Event bus: handler for '%s' failed (attempt %d/%d, event_id=%s): %s",
                event.agent_id,
                attempt,
                MAX_HANDLER_RETRIES,
                event.event_id,
                exc,
            )
            if attempt < MAX_HANDLER_RETRIES:
                await asyncio.sleep(delay)

    # All retries exhausted → dead-letter queue
    logger.error(
        "Event bus: handler for '%s' failed after %d attempts "
        "(event_id=%s) → DLQ",
        event.agent_id,
        MAX_HANDLER_RETRIES,
        event.event_id,
    )
    event.attempt = MAX_HANDLER_RETRIES
    if len(dead_letter_queue) >= _DLQ_MAX_SIZE:
        dead_letter_queue.pop(0)  # Prune oldest when DLQ is full
    dead_letter_queue.append(event)


def dlq_snapshot() -> List[Dict[str, Any]]:
    """Return a JSON-friendly snapshot of the dead-letter queue.

    Useful for monitoring dashboards and health endpoints.
    """
    return [e.to_dict() for e in dead_letter_queue]
