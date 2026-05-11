"""
Connection fixer for network and WebSocket connection issues.

Automatically detects and fixes:
  - WebSocket disconnections
  - Network timeouts
  - Connection pool exhaustion
  - DNS resolution failures
"""

import asyncio
import logging
from typing import Callable, Coroutine, Optional

from errors.decorators import retry_on_failure
from errors.exceptions import NetworkError, TimeoutError as SovereigntyTimeoutError

log = logging.getLogger("fixers.connection")


class ConnectionFixer:
    """
    Monitors and repairs network connections automatically.
    """

    def __init__(
        self,
        max_retries: int = 5,
        retry_delay: float = 2.0,
        health_check_interval: float = 30.0,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.health_check_interval = health_check_interval

        self._is_healthy = True
        self._connection_failures = 0
        self._last_failure_time: Optional[float] = None
        self._monitor_task: Optional[asyncio.Task] = None

    async def fix_connection(
        self,
        connect_func: Callable[[], Coroutine],
        test_func: Optional[Callable[[], Coroutine]] = None,
    ) -> bool:
        """
        Attempt to fix a broken connection.

        Args:
            connect_func: Async function to establish connection
            test_func: Optional async function to test connection

        Returns:
            True if connection was fixed, False otherwise
        """
        log.info("Attempting to fix connection...")

        for attempt in range(self.max_retries):
            try:
                # Attempt to reconnect
                await connect_func()

                # Test connection if test function provided
                if test_func:
                    await asyncio.wait_for(test_func(), timeout=5.0)

                log.info("Connection fixed successfully")
                self._is_healthy = True
                self._connection_failures = 0
                return True

            except asyncio.TimeoutError:
                log.warning("Connection test timeout (attempt %d/%d)", attempt + 1, self.max_retries)
            except Exception as e:
                log.warning("Connection fix failed (attempt %d/%d): %s", attempt + 1, self.max_retries, e)

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        log.error("Failed to fix connection after %d attempts", self.max_retries)
        self._is_healthy = False
        self._connection_failures += 1
        return False

    @retry_on_failure(max_retries=3, base_delay=1.0)
    async def ensure_connected(
        self,
        connect_func: Callable[[], Coroutine],
        is_connected_func: Callable[[], bool],
    ) -> None:
        """
        Ensure connection is established, reconnecting if necessary.

        Args:
            connect_func: Async function to establish connection
            is_connected_func: Function to check if connected

        Raises:
            NetworkError: If connection cannot be established
        """
        if is_connected_func():
            return

        try:
            await asyncio.wait_for(connect_func(), timeout=10.0)
        except asyncio.TimeoutError as e:
            raise SovereigntyTimeoutError("Connection timeout", timeout=10.0) from e
        except Exception as e:
            raise NetworkError(f"Connection failed: {e}") from e

        if not is_connected_func():
            raise NetworkError("Connection established but health check failed")

    async def monitor_connection(
        self,
        health_check_func: Callable[[], Coroutine[any, any, bool]],
        fix_func: Optional[Callable[[], Coroutine]] = None,
    ) -> None:
        """
        Monitor connection health and auto-fix if needed.

        Args:
            health_check_func: Async function that returns connection health status
            fix_func: Optional async function to fix connection when unhealthy
        """
        log.info("Starting connection monitoring (interval=%.1fs)", self.health_check_interval)

        while True:
            try:
                is_healthy = await asyncio.wait_for(
                    health_check_func(), timeout=self.health_check_interval
                )

                if not is_healthy and fix_func:
                    log.warning("Connection unhealthy, attempting to fix...")
                    await fix_func()

                self._is_healthy = is_healthy

            except asyncio.CancelledError:
                log.info("Connection monitoring stopped")
                raise
            except Exception as e:
                log.error("Connection health check failed: %s", e)
                self._is_healthy = False

            await asyncio.sleep(self.health_check_interval)

    async def start_monitoring(
        self,
        health_check_func: Callable[[], Coroutine[any, any, bool]],
        fix_func: Optional[Callable[[], Coroutine]] = None,
    ) -> None:
        """Start background connection monitoring."""
        if self._monitor_task and not self._monitor_task.done():
            log.warning("Connection monitoring already running")
            return

        self._monitor_task = asyncio.create_task(
            self.monitor_connection(health_check_func, fix_func)
        )

    async def stop_monitoring(self) -> None:
        """Stop background connection monitoring."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    def status(self) -> dict:
        """Get current connection fixer status."""
        return {
            "is_healthy": self._is_healthy,
            "connection_failures": self._connection_failures,
            "last_failure_time": self._last_failure_time,
            "monitoring": self._monitor_task is not None and not self._monitor_task.done(),
        }
