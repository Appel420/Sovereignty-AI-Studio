"""
watchers/health_watcher.py
===========================
Monitors the health of all Sovereignty AI Studio services.

Services monitored (with configurable URLs):
    - bridge.py WebSocket     (ws://localhost:9897)
    - Node.js node-bridge     (http://localhost:9899/health)

Each service is polled via an HTTP HEAD / GET request every
*check_interval* seconds.  The watcher maintains a :class:`ServiceHealth`
status object for each service and fires registered callbacks when status
transitions occur (e.g. HEALTHY → DEGRADED, DEGRADED → DOWN).

Usage::

    watcher = HealthWatcher()
    watcher.on_status_change(lambda name, health: print(f"{name}: {health.status}"))
    await watcher.start()
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
import urllib.request
import urllib.error

log = logging.getLogger(__name__)

# Default health-check interval in seconds
_DEFAULT_CHECK_INTERVAL: float = 15.0

# Number of consecutive failures before status degrades / declares DOWN
_DEGRADED_THRESHOLD: int = 2
_DOWN_THRESHOLD: int = 4


class HealthStatus(enum.Enum):
    """Health status values for a monitored service."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class ServiceHealth:
    """Current health snapshot for one monitored service.

    Attributes:
        name:              Human-readable service name.
        url:               Health-check URL polled.
        status:            Current :class:`HealthStatus`.
        last_check:        Unix timestamp of the last check attempt.
        consecutive_fails: Number of consecutive failed checks.
        last_error:        Error message from the last failure (or empty).
        latency_ms:        Round-trip latency of the last successful check.
    """

    name: str
    url: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: float = 0.0
    consecutive_fails: int = 0
    last_error: str = ""
    latency_ms: float = 0.0


# Callback type: (service_name, health) → None (sync or async)
StatusChangeCallback = Callable[[str, ServiceHealth], None]


class HealthWatcher:
    """Polls service health endpoints and reports status changes.

    Args:
        check_interval: Seconds between successive rounds of health checks.
        timeout:        HTTP request timeout in seconds.

    Example::

        watcher = HealthWatcher(check_interval=10.0)
        watcher.add_service("node-bridge", "http://localhost:9899/health")
        watcher.on_status_change(lambda name, h: log.warning("%s is %s", name, h.status))
        await watcher.start()
    """

    # Well-known services pre-loaded from the port layout.
    # bridge.py (9897) is WebSocket-only — no HTTP health endpoint.
    # node-bridge (9899) is the single HTTP-accessible health endpoint.
    DEFAULT_SERVICES: Dict[str, str] = {
        "node-bridge": "http://localhost:9899/health",
    }

    def __init__(
        self,
        check_interval: float = _DEFAULT_CHECK_INTERVAL,
        timeout: float = 5.0,
    ) -> None:
        self.check_interval = check_interval
        self.timeout = timeout
        self._services: Dict[str, ServiceHealth] = {}
        self._callbacks: List[StatusChangeCallback] = []
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # Pre-register well-known services
        for name, url in self.DEFAULT_SERVICES.items():
            self.add_service(name, url)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_service(self, name: str, url: str) -> None:
        """Register a service for health monitoring.

        Args:
            name: Human-readable service name (used in logs and callbacks).
            url:  HTTP URL to poll (should return 2xx when healthy).
        """
        self._services[name] = ServiceHealth(name=name, url=url)
        log.debug("HealthWatcher: registered service '%s' at %s", name, url)

    def on_status_change(self, callback: StatusChangeCallback) -> StatusChangeCallback:
        """Register a callback fired on every status transition.

        Args:
            callback: Called with ``(service_name, ServiceHealth)`` whenever
                      the service status changes.  Both sync and async
                      callables are supported.

        Returns the callback unchanged so decorator usage works.
        """
        self._callbacks.append(callback)
        return callback

    def get_status(self, name: str) -> Optional[ServiceHealth]:
        """Return the current :class:`ServiceHealth` for *name*, or None."""
        return self._services.get(name)

    def all_healthy(self) -> bool:
        """Return True only if every registered service is HEALTHY."""
        return all(
            s.status == HealthStatus.HEALTHY for s in self._services.values()
        )

    def summary(self) -> Dict[str, str]:
        """Return a dict of service_name → status_string for quick inspection."""
        return {name: h.status.value for name, h in self._services.items()}

    async def start(self) -> None:
        """Begin health checking in a background asyncio task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._check_loop(), name="health_watcher")
        log.info(
            "HealthWatcher started: monitoring %d service(s) every %.0fs",
            len(self._services),
            self.check_interval,
        )

    async def stop(self) -> None:
        """Stop the background health-check task gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("HealthWatcher stopped.")

    # ------------------------------------------------------------------
    # Internal check loop
    # ------------------------------------------------------------------

    async def _check_loop(self) -> None:
        """Background loop: run all health checks every *check_interval* seconds."""
        while self._running:
            await self._check_all()
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

    async def _check_all(self) -> None:
        """Fire off health checks for all registered services concurrently."""
        tasks = [
            asyncio.create_task(self._check_one(health))
            for health in self._services.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_one(self, health: ServiceHealth) -> None:
        """Perform a single HTTP health check for *health*.

        Updates :attr:`ServiceHealth.status` and calls callbacks if the
        status has changed.
        """
        prev_status = health.status
        t0 = time.monotonic()

        try:
            # Use asyncio executor so urllib doesn't block the event loop
            loop = asyncio.get_running_loop()
            status_code = await loop.run_in_executor(
                None, self._http_check, health.url
            )
            latency_ms = (time.monotonic() - t0) * 1000.0

            health.last_check = time.time()
            health.latency_ms = latency_ms

            if 200 <= status_code < 300:
                # Only 2xx responses indicate a healthy service.
                # 3xx redirects are not considered healthy — a health endpoint
                # should respond directly, not redirect.
                health.consecutive_fails = 0
                health.last_error = ""
                health.status = HealthStatus.HEALTHY
            else:
                health.consecutive_fails += 1
                health.last_error = f"HTTP {status_code}"
                health.status = self._degraded_or_down(health.consecutive_fails)

        except Exception as exc:  # noqa: BLE001
            health.consecutive_fails += 1
            health.last_error = str(exc)
            health.last_check = time.time()
            health.status = self._degraded_or_down(health.consecutive_fails)

        if health.status != prev_status:
            log.info(
                "HealthWatcher: '%s' %s → %s  (fails=%d, err=%s)",
                health.name,
                prev_status.value,
                health.status.value,
                health.consecutive_fails,
                health.last_error or "none",
            )
            self._emit_status_change(health.name, health)

    def _http_check(self, url: str) -> int:
        """Synchronous HTTP check; run in a thread pool to avoid blocking."""
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code

    @staticmethod
    def _degraded_or_down(consecutive_fails: int) -> HealthStatus:
        """Map failure count to an appropriate :class:`HealthStatus`.

        - 1 to ``_DEGRADED_THRESHOLD - 1`` failures → DEGRADED (transient blip)
        - ``_DEGRADED_THRESHOLD`` to ``_DOWN_THRESHOLD - 1`` → sustained DEGRADED
        - ``_DOWN_THRESHOLD`` or more → DOWN
        """
        if consecutive_fails >= _DOWN_THRESHOLD:
            return HealthStatus.DOWN
        if consecutive_fails >= _DEGRADED_THRESHOLD:
            return HealthStatus.DEGRADED
        # First failure (consecutive_fails == 1) is still DEGRADED — service may
        # recover on the next poll.
        return HealthStatus.DEGRADED

    def _emit_status_change(self, name: str, health: ServiceHealth) -> None:
        """Call all registered status-change callbacks."""
        for cb in self._callbacks:
            try:
                result = cb(name, health)
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)
            except Exception as exc:  # noqa: BLE001
                log.warning("HealthWatcher callback error: %s", exc)
