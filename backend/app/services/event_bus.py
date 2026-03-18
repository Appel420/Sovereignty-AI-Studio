"""
Async event bus — inter-agent communication via asyncio.Queue.
Supports publish/subscribe with optional topic filtering.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class Event:
    topic: str
    payload: Any
    source: str = "system"
    event_id: str = field(default_factory=lambda: _new_id())
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


def _new_id() -> str:
    import secrets
    return secrets.token_hex(8)


class EventBus:
    """
    Lightweight asyncio-based pub/sub event bus.

    Usage:
        bus = EventBus()
        sub_id = await bus.subscribe("agent.result", my_handler)
        await bus.publish(Event(topic="agent.result", payload={...}))
        await bus.unsubscribe(sub_id)
    """

    def __init__(self, queue_size: int = 1000):
        self._subscribers: Dict[str, List[Dict]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop())
        logger.info("EventBus started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")

    async def publish(self, event: Event) -> None:
        """Enqueue an event for async delivery to subscribers."""
        try:
            await self._queue.put(event)
        except asyncio.QueueFull:
            logger.warning("EventBus queue full — dropping event topic=%s", event.topic)

    def publish_sync(self, event: Event) -> None:
        """Non-async publish (best-effort, may drop if queue full)."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("EventBus queue full (sync) — dropping event topic=%s", event.topic)

    async def subscribe(self, topic: str, handler: Callable) -> str:
        """Register a handler for a topic. Returns subscription ID."""
        sub_id = _new_id()
        self._subscribers.setdefault(topic, []).append(
            {"id": sub_id, "handler": handler}
        )
        logger.debug("EventBus: subscribed %s to topic=%s", sub_id, topic)
        return sub_id

    async def unsubscribe(self, sub_id: str) -> None:
        for topic, subs in self._subscribers.items():
            self._subscribers[topic] = [s for s in subs if s["id"] != sub_id]

    async def _dispatch_loop(self) -> None:
        while self._running:
            try:
                event: Event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._deliver(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("EventBus dispatch error: %s", exc)

    async def _deliver(self, event: Event) -> None:
        handlers = (
            self._subscribers.get(event.topic, [])
            + self._subscribers.get("*", [])
        )
        for sub in handlers:
            try:
                result = sub["handler"](event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error(
                    "EventBus handler error topic=%s sub=%s: %s",
                    event.topic, sub["id"], exc,
                )

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def subscriber_count(self) -> int:
        return sum(len(v) for v in self._subscribers.values())


# Module-level singleton started by FastAPI lifespan
event_bus = EventBus()
