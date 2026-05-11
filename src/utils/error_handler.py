"""
Sovereignty AI Studio — Centralized Error Handler.

Provides structured error categories, a SovereignError hierarchy,
exponential-backoff retry helpers, and an ErrorHandler class that
logs, records, and optionally publishes errors to the EventBus.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Type

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error categories
# ---------------------------------------------------------------------------

class ErrorCategory(Enum):
    """Categorises errors by origin and severity."""

    NETWORK = "network"
    AUTH = "auth"
    AI_PROVIDER = "ai_provider"
    MEMORY = "memory"
    TOKEN = "token"
    PLUGIN = "plugin"
    VALIDATION = "validation"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Structured exception hierarchy
# ---------------------------------------------------------------------------

class SovereignError(Exception):
    """Base structured error for all Sovereignty AI Studio modules."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        *,
        original: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.original = original
        self.context: Dict[str, Any] = context or {}
        self.timestamp: float = time.time()

    def as_dict(self) -> Dict[str, Any]:
        """Serialise the error to a plain dict suitable for JSON or EventBus."""
        return {
            "error": str(self),
            "category": self.category.value,
            "context": self.context,
            "timestamp": self.timestamp,
            "original": str(self.original) if self.original else None,
        }


class NetworkError(SovereignError):
    """Raised on connection or HTTP transport failures."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, ErrorCategory.NETWORK, **kwargs)


class AuthError(SovereignError):
    """Raised on authentication or authorisation failures."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, ErrorCategory.AUTH, **kwargs)


class AIProviderError(SovereignError):
    """Raised when an AI provider (local or API) fails to respond."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, ErrorCategory.AI_PROVIDER, **kwargs)


class MemoryError(SovereignError):
    """Raised on memory store read/write failures."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, ErrorCategory.MEMORY, **kwargs)


class TokenError(SovereignError):
    """Raised on token validation or quota failures."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, ErrorCategory.TOKEN, **kwargs)


class ValidationError(SovereignError):
    """Raised when input data fails validation."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, ErrorCategory.VALIDATION, **kwargs)


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

async def retry_async(
    fn: Callable,
    *args: Any,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """
    Retry an async callable with exponential back-off.

    :param fn:         Async callable to retry.
    :param retries:    Maximum number of attempts (including the first).
    :param delay:      Initial wait (seconds) between attempts.
    :param backoff:    Multiplier applied to *delay* after each failure.
    :param exceptions: Exception types to catch and retry on.
    :returns:          Return value of *fn* on success.
    :raises:           The last caught exception when all retries are exhausted.
    """
    wait = delay
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            return await fn(*args, **kwargs)
        except exceptions as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                log.warning(
                    "Attempt %d/%d failed (%s). Retrying in %.1fs…",
                    attempt, retries, exc, wait,
                )
                await asyncio.sleep(wait)
                wait *= backoff
            else:
                log.error(
                    "All %d attempts exhausted for %s: %s",
                    retries, getattr(fn, "__name__", repr(fn)), exc,
                )
    raise last_exc  # type: ignore[misc]


def retry_sync(
    fn: Callable,
    *args: Any,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """
    Retry a synchronous callable with exponential back-off.

    Same parameters as :func:`retry_async`, but synchronous.
    """
    wait = delay
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except exceptions as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                log.warning(
                    "Attempt %d/%d failed (%s). Retrying in %.1fs…",
                    attempt, retries, exc, wait,
                )
                time.sleep(wait)
                wait *= backoff
            else:
                log.error(
                    "All %d attempts exhausted for %s: %s",
                    retries, getattr(fn, "__name__", repr(fn)), exc,
                )
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Central error handler
# ---------------------------------------------------------------------------

class ErrorHandler:
    """
    Centralised error handler: structures, logs, records, and optionally
    publishes errors to the EventBus for downstream listeners.

    Usage::

        handler = ErrorHandler(bus=event_bus)
        try:
            risky_call()
        except Exception as exc:
            handler.handle(exc, context={"module": "bridge"})
    """

    def __init__(self, bus: Any = None) -> None:
        self._bus = bus
        self._history: list[Dict[str, Any]] = []
        self._max_history = 500

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None,
        *,
        reraise: bool = False,
    ) -> Dict[str, Any]:
        """
        Log and record an exception, then optionally publish it to the bus.

        :param exc:     The exception to handle.
        :param context: Optional metadata dict (module, user, etc.).
        :param reraise: Re-raise *exc* after recording it.
        :returns:       Structured error dict.
        """
        if isinstance(exc, SovereignError):
            category = exc.category.value
            if context:
                exc.context.update(context)
            error_dict = exc.as_dict()
        else:
            category = ErrorCategory.UNKNOWN.value
            error_dict = {
                "error": str(exc),
                "category": category,
                "context": context or {},
                "timestamp": time.time(),
                "original": None,
                "traceback": traceback.format_exc(),
            }

        log.error("[%s] %s | context=%s", category.upper(), exc, context)
        self._record(error_dict)

        if self._bus is not None:
            self._bus.publish_sync("error", error_dict)

        if reraise:
            raise exc

        return error_dict

    def recent_errors(self, limit: int = 20) -> list[Dict[str, Any]]:
        """Return the *limit* most recent error records."""
        return list(self._history[-limit:])

    def clear(self) -> None:
        """Clear the internal error history."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _record(self, entry: Dict[str, Any]) -> None:
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-(self._max_history // 2):]
