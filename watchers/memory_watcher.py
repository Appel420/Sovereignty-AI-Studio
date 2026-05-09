"""
MemoryWatcher — watches the MemoryStore for change events and fan-outs.

Polls the event log at configurable intervals and forwards new events
to the EventBus so other modules can react to memory changes.

Usage:
    store = MemoryStore()
    await store.init()
    bus = EventBus()
    watcher = MemoryWatcher(store, bus)
    await watcher.start()
"""

import asyncio
import logging
import time
from typing import Optional

log = logging.getLogger("watchers.memory")


class MemoryWatcher:
    """
    Polls MemoryStore.get_events() and publishes new events to an EventBus.
    Avoids re-publishing events that have already been dispatched.
    """

    def __init__(
        self,
        store,
        bus,
        poll_interval: float = 5.0,
    ) -> None:
        self._store = store
        self._bus = bus
        self._interval = poll_interval
        self._task: Optional[asyncio.Task] = None
        self._last_seen_ts: int = int(time.time() * 1000)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="memory_watcher")
        log.info("MemoryWatcher started (poll=%.1fs)", self._interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("MemoryWatcher stopped")

    async def _run(self) -> None:
        while True:
            try:
                await self._poll()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.debug("Error during memory event polling: %s", exc)
            await asyncio.sleep(self._interval)

    async def _poll(self) -> None:
        events = await self._store.get_events(limit=50)
        new_events = [e for e in events if e["ts"] > self._last_seen_ts]
        if new_events:
            self._last_seen_ts = max(e["ts"] for e in new_events)
            for event in reversed(new_events):  # oldest first
                await self._bus.publish(
                    "memory_event",
                    {
                        "event_type": event["type"],
                        "payload": event.get("payload", {}),
                        "ts": event["ts"],
                    },
                )
                log.debug("MemoryWatcher dispatched: %s", event["type"])

    def status(self) -> dict:
        return {
            "poll_interval_s": self._interval,
            "last_seen_ts": self._last_seen_ts,
            "running": self._task is not None and not self._task.done(),
        }
