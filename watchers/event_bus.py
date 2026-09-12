"""
EventBus — in-process async pub/sub for agent coordination.

Agents and services can subscribe to typed events and publish to them.
Events are dispatched to all subscribers of a given type.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

log = logging.getLogger("watchers.event_bus")
Handler = Callable[[dict[str, Any]], Coroutine | None]


class EventBus:
    """Lightweight async pub/sub event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._history: list[dict[str, Any]] = []
        self._max_history = 200

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register a handler for ``event_type``; ``*`` receives all events."""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            log.debug("Subscribed %s → %s", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        """Remove a previously registered handler."""
        try:
            self._subscribers[event_type].remove(handler)
        except ValueError:
            pass

    def unsubscribe_all(self, handler: Handler) -> None:
        """Remove a handler from every event type."""
        for handlers in self._subscribers.values():
            try:
                handlers.remove(handler)
            except ValueError:
                pass

    async def publish(self, event_type: str, payload: dict[str, Any]) -> int:
        """Publish an event and return the number of handlers invoked."""
        event = {"type": event_type, **payload}
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        handlers = list(self._subscribers.get(event_type, []))
        handlers += [h for h in self._subscribers.get("*", []) if h not in handlers]

        count = 0
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
                count += 1
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # A subscriber must not be able to terminate the event bus.
                log.warning(
                    "Handler %s raised exception for event type %s: %s",
                    handler,
                    event_type,
                    exc,
                )
        return count

    def publish_sync(self, event_type: str, payload: dict[str, Any]) -> None:
        """Schedule ``publish`` from synchronous code when a loop is running."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(event_type, payload))
        except RuntimeError:
            log.warning("No running event loop — event %s dropped", event_type)

    def subscriber_count(self, event_type: str | None = None) -> int:
        """Return the number of subscribers for one event or all events."""
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(handlers) for handlers in self._subscribers.values())

    def history(self, event_type: str | None = None, limit: int = 50) -> list[dict]:
        """Return recent history, optionally filtered by event type."""
        items = (
            [event for event in self._history if event.get("type") == event_type]
            if event_type
            else list(self._history)
        )
        return items[-limit:]

    def status(self) -> dict:
        """Return subscription and history status."""
        return {
            "subscriptions": {k: len(v) for k, v in self._subscribers.items() if v},
            "history_count": len(self._history),
        }
