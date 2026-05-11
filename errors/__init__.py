"""
Sovereignty AI Studio — Error Handling Module

Provides custom exceptions, error handlers, and error recovery utilities:
  - Custom exception hierarchy for different error types
  - Error handlers with retry logic and fallback mechanisms
  - Error logging and monitoring integration
  - Graceful degradation support
"""

from .exceptions import (
    SovereigntyError,
    BridgeError,
    MemoryError,
    TokenError,
    AIModelError,
    WatcherError,
    ValidationError,
    ConfigurationError,
    NetworkError,
    TimeoutError,
)
from .handlers import (
    ErrorHandler,
    RetryHandler,
    FallbackHandler,
    CircuitBreaker,
)
from .decorators import (
    handle_errors,
    retry_on_failure,
    fallback_on_error,
    log_errors,
)

__all__ = [
    # Exceptions
    "SovereigntyError",
    "BridgeError",
    "MemoryError",
    "TokenError",
    "AIModelError",
    "WatcherError",
    "ValidationError",
    "ConfigurationError",
    "NetworkError",
    "TimeoutError",
    # Handlers
    "ErrorHandler",
    "RetryHandler",
    "FallbackHandler",
    "CircuitBreaker",
    # Decorators
    "handle_errors",
    "retry_on_failure",
    "fallback_on_error",
    "log_errors",
]
