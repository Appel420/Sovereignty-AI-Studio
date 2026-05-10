"""
ErrorListener — subscribes to 'error' events on the EventBus and
aggregates them for dashboards and alerting.

Usage::

    bus = EventBus()
    listener = ErrorListener(bus, alert_threshold=10)
    await listener.start()
    # ...
    await listener.stop()
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("watchers.error_listener")

_MAX_ERRORS = 1000


class ErrorListener:
    """
    Listens for ``'error'`` events published on an :class:`EventBus` instance.

    * Aggregates error counts by category.
    * Fires optional alert callbacks when a category's error count crosses
      *alert_threshold*.
    * Logs a periodic summary of counts (every 60 s) for operational visibility.
    """

    def __init__(self, bus: Any, alert_threshold: int = 10) -> None:
        self._bus = bus
        self._alert_threshold = alert_threshold
        self._errors: List[Dict[str, Any]] = []
        self._counts: Dict[str, int] = {}
        self._alert_callbacks: List[Callable[..., None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        self._started_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Register the error handler and start the background flush loop."""
        self._bus.subscribe("error", self._on_error)
        self._running = True
        self._started_at = time.time()
        self._task = asyncio.create_task(self._flush_loop(), name="error_listener")
        log.info("ErrorListener started (alert_threshold=%d)", self._alert_threshold)

    async def stop(self) -> None:
        """Unregister the error handler and stop the background loop."""
        self._running = False
        self._bus.unsubscribe("error", self._on_error)
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("ErrorListener stopped")

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------

    def _on_error(self, event: Dict[str, Any]) -> None:
        """Called synchronously by the EventBus for each 'error' event."""
        category = str(event.get("category", "unknown"))

        self._errors.append(event)
        self._counts[category] = self._counts.get(category, 0) + 1

        # Keep memory bounded
        if len(self._errors) > _MAX_ERRORS:
            self._errors = self._errors[-(_MAX_ERRORS // 2):]

        log.warning(
            "[ErrorListener] %s | category=%s | total=%d",
            event.get("error", "?"),
            category,
            self._counts[category],
        )

        if self._counts[category] >= self._alert_threshold:
            self._trigger_alert(category)

    def _trigger_alert(self, category: str) -> None:
        count = self._counts[category]
        msg = (
            f"ErrorListener: '{category}' error threshold reached "
            f"({count} occurrences)."
        )
        log.error(msg)
        for cb in list(self._alert_callbacks):
            try:
                cb(category, count, msg)
            except Exception as exc:  # noqa: BLE001
                log.debug("Alert callback raised: %s", exc)

    # ------------------------------------------------------------------
    # Alert callbacks
    # ------------------------------------------------------------------

    def add_alert_callback(self, callback: Callable[..., None]) -> None:
        """Register a ``callback(category: str, count: int, message: str)``."""
        if callback not in self._alert_callbacks:
            self._alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[..., None]) -> None:
        """Remove a previously registered alert callback."""
        try:
            self._alert_callbacks.remove(callback)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Background periodic summary
    # ------------------------------------------------------------------

    async def _flush_loop(self) -> None:
        """Log a periodic summary of error counts every 60 seconds."""
        while self._running:
            try:
                await asyncio.sleep(60)
                if self._counts:
                    summary = ", ".join(
                        f"{k}={v}" for k, v in sorted(self._counts.items())
                    )
                    log.info("[ErrorListener] 60s summary — %s", summary)
            except asyncio.CancelledError:
                raise

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent *limit* error events."""
        return list(self._errors[-limit:])

    def counts(self) -> Dict[str, int]:
        """Return error counts keyed by category."""
        return dict(self._counts)

    def status(self) -> Dict[str, Any]:
        """Return a status summary suitable for health-check endpoints."""
        return {
            "running": self._running,
            "total_errors": len(self._errors),
            "counts_by_category": self.counts(),
            "alert_threshold": self._alert_threshold,
            "started_at": self._started_at,
        }
