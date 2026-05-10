"""
watchers/event_listener.py
===========================
Central async event listener that dispatches inbound events to registered
handler functions (agents, watchers, or any callable).

Architecture
------------
The listener owns a single asyncio.Queue.  Any component running on the
**same event loop thread** can push an event via :meth:`EventListener.emit`
(awaitable) or :meth:`EventListener.emit_nowait` (sync, same thread).

For cross-thread emission (e.g. from a background thread), use
:meth:`EventListener.emit_threadsafe`, which uses
``loop.call_soon_threadsafe`` to safely enqueue the event from another OS
thread.

Failed handlers are retried up to *max_retries* times.  Events that exhaust
all retries land in the *dead_letter_queue* list for inspection.

Usage::

    listener = EventListener()

    @listener.on("ai_response")
    async def handle_ai(event):
        print("AI said:", event["data"]["text"])

    await listener.start()
    await listener.emit("ai_response", {"text": "Hello!"})
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

# Maximum number of retry attempts for a failing handler
_DEFAULT_MAX_RETRIES: int = 3

# Seconds to wait between retry attempts (exponential backoff applied)
_RETRY_BASE_DELAY: float = 0.5

# Maximum events to hold in the dead-letter queue before dropping oldest
_DLQ_MAX_SIZE: int = 200


# ---------------------------------------------------------------------------
# Event data model
# ---------------------------------------------------------------------------
@dataclass
class Event:
    """A typed event dispatched through the :class:`EventListener`.

    Attributes:
        event_type: String identifier used to route the event (e.g. ``"ai_response"``).
        data:       Arbitrary payload dict.
        source:     Optional identifier of the emitting component.
        timestamp:  Unix timestamp of emission.
        attempt:    Current delivery attempt number (starts at 1).
    """

    event_type: str
    data: Dict[str, Any]
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    attempt: int = 1


# Type alias for event handler coroutines
EventHandler = Callable[[Event], Any]


# ---------------------------------------------------------------------------
# EventListener
# ---------------------------------------------------------------------------
class EventListener:
    """Central async event bus with type-based routing and dead-letter handling.

    Args:
        max_retries:  Maximum delivery attempts per event before DLQ.
        queue_size:   Internal asyncio.Queue max size (0 = unlimited).

    Example::

        listener = EventListener()

        @listener.on("file_changed")
        async def reload(event):
            await config.reload(event.data["path"])

        await listener.start()

        # From anywhere in the codebase:
        await listener.emit("file_changed", {"path": "config.json"})
    """

    def __init__(
        self,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        queue_size: int = 0,
    ) -> None:
        self.max_retries = max_retries
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.dead_letter_queue: List[Event] = []
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def on(
        self, event_type: str
    ) -> Callable[[EventHandler], EventHandler]:
        """Decorator that registers a handler for *event_type*.

        Multiple handlers may be registered for the same event type;
        they are called sequentially in registration order.

        Example::

            @listener.on("health_change")
            async def alert(event): ...
        """
        def decorator(func: EventHandler) -> EventHandler:
            self.register(event_type, func)
            return func
        return decorator

    def register(self, event_type: str, handler: EventHandler) -> None:
        """Register *handler* for *event_type* (programmatic alternative to decorator).

        Args:
            event_type: String event type identifier.
            handler:    Coroutine function called with the :class:`Event`.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        log.debug("EventListener: registered handler for '%s'", event_type)

    # ------------------------------------------------------------------
    # Emitting events
    # ------------------------------------------------------------------

    async def emit(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        source: str = "unknown",
    ) -> None:
        """Enqueue an event for async dispatch.

        This method is async but returns immediately after enqueuing —
        it does not wait for handlers to finish.

        Args:
            event_type: Routing key for handler lookup.
            data:       Arbitrary payload dict.
            source:     Identifier of the emitting component.
        """
        event = Event(
            event_type=event_type,
            data=data or {},
            source=source,
        )
        await self._queue.put(event)
        log.debug(
            "EventListener: queued '%s' from '%s' (qsize=%d)",
            event_type,
            source,
            self._queue.qsize(),
        )

    def emit_nowait(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        source: str = "unknown",
    ) -> None:
        """Non-blocking variant of :meth:`emit` — safe to call from sync code
        on the **same event loop thread**.

        Raises ``asyncio.QueueFull`` if the queue is full and *queue_size* > 0.
        """
        event = Event(event_type=event_type, data=data or {}, source=source)
        self._queue.put_nowait(event)

    def emit_threadsafe(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        source: str = "unknown",
    ) -> None:
        """Thread-safe event emission for use from non-event-loop threads.

        Uses ``loop.call_soon_threadsafe`` to schedule the enqueue on the
        event loop.  Must be called after :meth:`start` (which captures the
        running loop).

        Raises:
            RuntimeError: If the listener has not been started yet.
        """
        if self._loop is None:
            raise RuntimeError(
                "EventListener.emit_threadsafe() called before start(). "
                "Call await listener.start() first."
            )
        event = Event(event_type=event_type, data=data or {}, source=source)
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background dispatch task."""
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(
            self._dispatch_loop(), name="event_listener"
        )
        log.info("EventListener started.")

    async def stop(self) -> None:
        """Drain the queue and stop the dispatch task gracefully.

        Sets ``_running = False`` and pushes a ``_stop`` sentinel so the
        dispatch loop exits cleanly after processing any already-queued events.
        Waits for the task to finish before returning.
        """
        self._running = False
        # Sentinel unblocks the queue.get() call inside _dispatch_loop
        await self._queue.put(
            Event(event_type="_stop", data={}, source="listener")
        )
        if self._task and not self._task.done():
            try:
                # Allow up to 5 s for the dispatch loop to drain and exit
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
        log.info(
            "EventListener stopped. DLQ size: %d", len(self.dead_letter_queue)
        )

    # ------------------------------------------------------------------
    # Dispatch loop
    # ------------------------------------------------------------------

    async def _dispatch_loop(self) -> None:
        """Continuously dequeue and dispatch events until stopped."""
        while self._running:
            try:
                event: Event = await self._queue.get()
            except asyncio.CancelledError:
                break

            if event.event_type == "_stop":
                break

            await self._dispatch(event)
            self._queue.task_done()

    async def _dispatch(self, event: Event) -> None:
        """Dispatch *event* to all registered handlers, with retry on failure."""
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            log.debug("EventListener: no handler for '%s' — dropping", event.event_type)
            return

        for handler in handlers:
            success = await self._call_with_retry(handler, event)
            if not success:
                self._send_to_dlq(event)

    async def _call_with_retry(
        self, handler: EventHandler, event: Event
    ) -> bool:
        """Call *handler* with exponential-backoff retries.

        Returns:
            True if the handler eventually succeeded, False after max retries.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
                return True
            except Exception as exc:  # noqa: BLE001
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning(
                    "EventListener: handler for '%s' failed (attempt %d/%d): %s — retrying in %.1fs",
                    event.event_type,
                    attempt,
                    self.max_retries,
                    exc,
                    delay,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)

        log.error(
            "EventListener: handler for '%s' failed after %d attempts — sending to DLQ",
            event.event_type,
            self.max_retries,
        )
        return False

    def _send_to_dlq(self, event: Event) -> None:
        """Append *event* to the dead-letter queue, pruning if necessary."""
        if len(self.dead_letter_queue) >= _DLQ_MAX_SIZE:
            self.dead_letter_queue.pop(0)  # Drop oldest
        self.dead_letter_queue.append(event)

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def registered_event_types(self) -> List[str]:
        """Return list of event types that have at least one handler."""
        return list(self._handlers.keys())

    def dlq_snapshot(self) -> List[Dict[str, Any]]:
        """Return a JSON-friendly snapshot of the dead-letter queue."""
        return [
            {
                "event_type": e.event_type,
                "source": e.source,
                "timestamp": e.timestamp,
                "data": e.data,
                "attempts": e.attempt,
            }
            for e in self.dead_letter_queue
        ]
