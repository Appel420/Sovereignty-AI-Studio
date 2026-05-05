"""
BridgeWatcher — monitors the WebSocket bridge connection health.

Runs as a background asyncio task alongside the bridge server.
Detects disconnections, tracks uptime/downtime, and notifies via EventBus.

Usage:
    bus = EventBus()
    watcher = BridgeWatcher(bus, bridge_url="ws://localhost:9897")
    await watcher.start()
    # ... later ...
    await watcher.stop()
"""

import asyncio
import logging
import time
from typing import Optional

log = logging.getLogger("watchers.bridge")


class BridgeWatcher:
    """
    Periodically checks bridge connectivity and publishes health events.
    Emits:
      bridge_up   — when the bridge comes online
      bridge_down — when the bridge goes offline
      bridge_ping — periodic heartbeat with latency info
    """

    def __init__(
        self,
        bus,
        bridge_url: str = "ws://localhost:9897",
        check_interval: float = 15.0,
        timeout: float = 5.0,
    ) -> None:
        self._bus = bus
        self._url = bridge_url
        self._interval = check_interval
        self._timeout = timeout
        self._task: Optional[asyncio.Task] = None
        self._is_up: Optional[bool] = None
        self._up_since: Optional[float] = None
        self._down_since: Optional[float] = None
        self._check_count = 0
        self._fail_count = 0

    async def start(self) -> None:
        """Start the background watcher task."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="bridge_watcher")
        log.info("BridgeWatcher started — monitoring %s", self._url)

    async def stop(self) -> None:
        """Stop the background watcher task."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("BridgeWatcher stopped")

    async def _run(self) -> None:
        while True:
            try:
                await self._check()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.debug("BridgeWatcher._run error: %s", exc)
            await asyncio.sleep(self._interval)

    async def _check(self) -> None:
        self._check_count += 1
        start = time.monotonic()
        up = await self._probe()
        latency_ms = round((time.monotonic() - start) * 1000, 1)

        if up and self._is_up is not True:
            # Transition: offline → online
            self._up_since = time.time()
            self._down_since = None
            self._is_up = True
            self._fail_count = 0
            await self._bus.publish("bridge_up", {
                "url": self._url,
                "latency_ms": latency_ms,
                "ts": int(time.time() * 1000),
            })
            log.info("Bridge UP: %s (%.1fms)", self._url, latency_ms)

        elif not up and self._is_up is not False:
            # Transition: online → offline
            self._down_since = time.time()
            self._up_since = None
            self._is_up = False
            await self._bus.publish("bridge_down", {
                "url": self._url,
                "ts": int(time.time() * 1000),
            })
            log.warning("Bridge DOWN: %s", self._url)

        if up:
            await self._bus.publish("bridge_ping", {
                "url": self._url,
                "latency_ms": latency_ms,
                "check_count": self._check_count,
                "ts": int(time.time() * 1000),
            })

    async def _probe(self) -> bool:
        """
        Try to open a WebSocket connection to the bridge.
        Returns True on success, False on any failure.
        """
        try:
            import websockets  # type: ignore[import]
            async with websockets.connect(
                self._url, open_timeout=self._timeout, close_timeout=2
            ):
                return True
        except Exception:
            self._fail_count += 1
            return False

    def status(self) -> dict:
        return {
            "url": self._url,
            "is_up": self._is_up,
            "up_since": self._up_since,
            "down_since": self._down_since,
            "check_count": self._check_count,
            "fail_count": self._fail_count,
            "check_interval_s": self._interval,
        }
