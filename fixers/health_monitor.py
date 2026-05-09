"""
Health monitor for overall system health and auto-recovery.

Monitors:
  - Connection health
  - Database health
  - Configuration validity
  - Model availability
  - Resource usage (memory, CPU)
  - Error rates
"""

import asyncio
import logging
import time
from typing import Callable, Coroutine, Optional

log = logging.getLogger("fixers.health")


class HealthMonitor:
    """
    Monitors overall system health and triggers auto-recovery.
    """

    def __init__(
        self,
        check_interval: float = 60.0,
        error_threshold: int = 10,
        auto_fix: bool = True,
    ):
        self.check_interval = check_interval
        self.error_threshold = error_threshold
        self.auto_fix = auto_fix

        self._is_healthy = True
        self._last_check_time: Optional[float] = None
        self._error_count = 0
        self._total_checks = 0
        self._monitor_task: Optional[asyncio.Task] = None
        self._health_checks: dict[str, Callable[[], Coroutine[any, any, bool]]] = {}
        self._fixers: dict[str, Callable[[], Coroutine]] = {}

    def register_health_check(
        self,
        name: str,
        check_func: Callable[[], Coroutine[any, any, bool]],
        fixer_func: Optional[Callable[[], Coroutine]] = None,
    ) -> None:
        """
        Register a health check function.

        Args:
            name: Name of the health check
            check_func: Async function that returns True if healthy
            fixer_func: Optional async function to fix issues
        """
        self._health_checks[name] = check_func
        if fixer_func:
            self._fixers[name] = fixer_func
        log.info("Registered health check: %s", name)

    def unregister_health_check(self, name: str) -> None:
        """Unregister a health check."""
        self._health_checks.pop(name, None)
        self._fixers.pop(name, None)
        log.info("Unregistered health check: %s", name)

    async def run_health_checks(self) -> dict[str, bool]:
        """
        Run all registered health checks.

        Returns:
            Dictionary mapping check names to health status
        """
        results = {}

        for name, check_func in self._health_checks.items():
            try:
                is_healthy = await asyncio.wait_for(check_func(), timeout=10.0)
                results[name] = is_healthy

                if not is_healthy:
                    log.warning("Health check failed: %s", name)
                    self._error_count += 1

                    # Auto-fix if enabled
                    if self.auto_fix and name in self._fixers:
                        log.info("Attempting auto-fix for: %s", name)
                        try:
                            await self._fixers[name]()
                            log.info("Auto-fix succeeded for: %s", name)
                        except Exception as e:
                            log.error("Auto-fix failed for %s: %s", name, e)

            except asyncio.TimeoutError:
                log.error("Health check timeout: %s", name)
                results[name] = False
                self._error_count += 1
            except Exception as e:
                log.error("Health check error for %s: %s", name, e)
                results[name] = False
                self._error_count += 1

        self._total_checks += 1
        self._last_check_time = time.time()

        # Update overall health status
        all_healthy = all(results.values()) if results else True
        self._is_healthy = all_healthy and self._error_count < self.error_threshold

        return results

    async def monitor_health(self) -> None:
        """
        Continuously monitor system health.
        """
        log.info("Starting health monitoring (interval=%.1fs)", self.check_interval)

        while True:
            try:
                results = await self.run_health_checks()

                healthy_count = sum(1 for v in results.values() if v)
                total_count = len(results)

                log.info(
                    "Health check complete: %d/%d healthy, overall=%s",
                    healthy_count,
                    total_count,
                    "HEALTHY" if self._is_healthy else "UNHEALTHY",
                )

            except asyncio.CancelledError:
                log.info("Health monitoring stopped")
                raise
            except Exception as e:
                log.error("Health monitoring error: %s", e)

            await asyncio.sleep(self.check_interval)

    async def start_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._monitor_task and not self._monitor_task.done():
            log.warning("Health monitoring already running")
            return

        self._monitor_task = asyncio.create_task(self.monitor_health())
        log.info("Health monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            log.info("Health monitoring stopped")

    def reset_error_count(self) -> None:
        """Reset error count."""
        self._error_count = 0
        log.info("Error count reset")

    def is_healthy(self) -> bool:
        """
        Check if system is healthy.

        Returns:
            True if system is healthy
        """
        return self._is_healthy

    def get_uptime(self) -> float:
        """
        Get uptime since last health check.

        Returns:
            Uptime in seconds
        """
        if self._last_check_time:
            return time.time() - self._last_check_time
        return 0.0

    def status(self) -> dict:
        """Get current health monitor status."""
        return {
            "is_healthy": self._is_healthy,
            "error_count": self._error_count,
            "error_threshold": self.error_threshold,
            "total_checks": self._total_checks,
            "last_check_time": self._last_check_time,
            "uptime_seconds": self.get_uptime(),
            "monitoring": self._monitor_task is not None and not self._monitor_task.done(),
            "registered_checks": list(self._health_checks.keys()),
            "auto_fix_enabled": self.auto_fix,
        }
