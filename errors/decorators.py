"""
Error handling decorators for async functions.

Provides convenient decorators for:
  - Automatic error handling with logging
  - Retry logic with exponential backoff
  - Fallback values on error
  - Combined error handling strategies
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, TypeVar

from .exceptions import SovereigntyError
from .handlers import RetryHandler, FallbackHandler

log = logging.getLogger("errors.decorators")

T = TypeVar("T")


def log_errors(
    logger: logging.Logger | None = None,
    context: str | None = None,
    reraise: bool = True,
) -> Callable:
    """
    Decorator to log errors from async functions.

    Args:
        logger: Logger to use (defaults to module logger)
        context: Context string for log messages
        reraise: Whether to re-raise the exception after logging
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            _logger = logger or log
            _context = context or f"{func.__module__}.{func.__name__}"

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                _logger.error("%s: %s", _context, e, exc_info=True)
                if reraise:
                    raise
                return None  # type: ignore

        return wrapper

    return decorator


def retry_on_failure(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    logger: logging.Logger | None = None,
) -> Callable:
    """
    Decorator to retry async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        logger: Logger to use for retry messages
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            handler = RetryHandler(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                logger=logger or log,
            )
            context = f"{func.__module__}.{func.__name__}"
            return await handler.execute(func, *args, context=context, **kwargs)

        return wrapper

    return decorator


def fallback_on_error(
    fallback: Any | Callable[[], Any],
    logger: logging.Logger | None = None,
) -> Callable:
    """
    Decorator to provide fallback value when async function fails.

    Args:
        fallback: Value or callable to use as fallback
        logger: Logger to use for error messages
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T | Any:
            handler = FallbackHandler(fallback=fallback, logger=logger or log)
            context = f"{func.__module__}.{func.__name__}"
            return await handler.execute(func, *args, context=context, **kwargs)

        return wrapper

    return decorator


def handle_errors(
    retry: bool = False,
    max_retries: int = 3,
    fallback: Any | None = None,
    logger: logging.Logger | None = None,
    reraise: bool = True,
) -> Callable:
    """
    Comprehensive error handling decorator combining multiple strategies.

    Args:
        retry: Enable retry logic
        max_retries: Maximum retry attempts if retry is enabled
        fallback: Fallback value if all retries fail
        logger: Logger to use
        reraise: Whether to re-raise exception if no fallback and all retries fail
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T | Any:
            _logger = logger or log
            context = f"{func.__module__}.{func.__name__}"

            async def execute() -> T:
                if retry:
                    handler = RetryHandler(max_retries=max_retries, logger=_logger)
                    return await handler.execute(func, *args, context=context, **kwargs)
                return await func(*args, **kwargs)

            try:
                return await execute()
            except Exception as e:
                _logger.error("%s: %s", context, e, exc_info=True)

                if fallback is not None:
                    if callable(fallback):
                        try:
                            result = fallback()
                            if asyncio.iscoroutine(result):
                                return await result
                            return result
                        except Exception as fb_error:
                            _logger.error("Fallback function failed: %s", fb_error)
                            if reraise:
                                raise e from fb_error
                    else:
                        _logger.info("Using fallback value: %s", fallback)
                        return fallback

                if reraise:
                    raise
                return None  # type: ignore

        return wrapper

    return decorator
