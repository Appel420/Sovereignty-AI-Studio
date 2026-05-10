"""
Error handlers with retry logic, fallback mechanisms, and circuit breakers.

Provides resilient error handling for async operations with:
  - Exponential backoff retry
  - Fallback value/function support
  - Circuit breaker pattern for failing services
  - Error aggregation and monitoring
"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, TypeVar

from .exceptions import SovereigntyError, TimeoutError as SovereigntyTimeoutError

log = logging.getLogger("errors.handlers")

T = TypeVar("T")


class ErrorHandler:
    """
    Base error handler with logging and error tracking.
    """

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or log
        self.error_count = 0
        self.last_error: Exception | None = None
        self.last_error_time: float | None = None

    def handle(self, error: Exception, context: str = "") -> None:
        """Log and track an error."""
        self.error_count += 1
        self.last_error = error
        self.last_error_time = time.time()
        self.logger.error("%s: %s", context or "Error", error, exc_info=True)

    def reset(self) -> None:
        """Reset error tracking."""
        self.error_count = 0
        self.last_error = None
        self.last_error_time = None

    def status(self) -> dict:
        """Return current error handler status."""
        return {
            "error_count": self.error_count,
            "last_error": str(self.last_error) if self.last_error else None,
            "last_error_time": self.last_error_time,
        }


class RetryHandler(ErrorHandler):
    """
    Error handler with exponential backoff retry logic.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        logger: logging.Logger | None = None,
    ):
        super().__init__(logger)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for given attempt."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        context: str = "",
        **kwargs: Any,
    ) -> T:
        """
        Execute an async function with retry logic.
        Raises the last exception if all retries are exhausted.
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.handle(e, context=f"{context} (attempt {attempt + 1}/{self.max_retries + 1})")

                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.logger.info("Retrying in %.2fs...", delay)
                    await asyncio.sleep(delay)
                else:
                    self.logger.error("All retry attempts exhausted for %s", context)

        # All retries failed
        if last_exception:
            raise last_exception
        raise SovereigntyError("Retry handler failed with no exception")


class FallbackHandler(ErrorHandler):
    """
    Error handler with fallback value or function support.
    """

    def __init__(
        self,
        fallback: Any | Callable[[], Any] | None = None,
        logger: logging.Logger | None = None,
    ):
        super().__init__(logger)
        self.fallback = fallback

    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        context: str = "",
        fallback: Any | None = None,
        **kwargs: Any,
    ) -> T | Any:
        """
        Execute an async function with fallback support.
        Returns the fallback value if the function raises an exception.
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self.handle(e, context=context)
            fb = fallback if fallback is not None else self.fallback

            if callable(fb):
                try:
                    result = fb()
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                except Exception as fb_error:
                    self.logger.error("Fallback function failed: %s", fb_error)
                    raise e from fb_error

            self.logger.info("Using fallback value: %s", fb)
            return fb


class CircuitBreaker:
    """
    Circuit breaker pattern for failing services.

    States:
      - CLOSED: normal operation, requests pass through
      - OPEN: too many failures, requests fail fast
      - HALF_OPEN: testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
        logger: logging.Logger | None = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.logger = logger or log

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        if self._state == "OPEN" and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                self.logger.info("Circuit breaker entering HALF_OPEN state")
        return self._state

    def _record_success(self) -> None:
        """Record a successful operation."""
        self._failure_count = 0
        if self._state == "HALF_OPEN":
            self._state = "CLOSED"
            self.logger.info("Circuit breaker recovered, entering CLOSED state")

    def _record_failure(self) -> None:
        """Record a failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            if self._state != "OPEN":
                self._state = "OPEN"
                self.logger.warning(
                    "Circuit breaker opened after %d failures", self._failure_count
                )

    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a function through the circuit breaker.
        Raises SovereigntyTimeoutError if circuit is OPEN.
        """
        if self.state == "OPEN":
            raise SovereigntyTimeoutError(
                "Circuit breaker is OPEN",
                timeout=self.recovery_timeout,
                details={"failure_count": self._failure_count},
            )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise e

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "CLOSED"
        self.logger.info("Circuit breaker manually reset to CLOSED")

    def status(self) -> dict:
        """Return current circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self._last_failure_time,
            "recovery_timeout": self.recovery_timeout,
        }
