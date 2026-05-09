"""
Custom exception hierarchy for Sovereignty AI Studio.

All custom exceptions derive from SovereigntyError for easy catching.
Each exception type maps to a specific subsystem or failure mode.
"""


class SovereigntyError(Exception):
    """Base exception for all Sovereignty AI Studio errors."""

    def __init__(self, message: str, code: str = "UNKNOWN", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        detail_str = f" ({self.details})" if self.details else ""
        return f"[{self.code}] {self.message}{detail_str}"


class BridgeError(SovereigntyError):
    """Errors related to WebSocket bridge operations."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="BRIDGE_ERROR", details=details)


class MemoryError(SovereigntyError):
    """Errors related to memory store operations."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="MEMORY_ERROR", details=details)


class TokenError(SovereigntyError):
    """Errors related to token management."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="TOKEN_ERROR", details=details)


class AIModelError(SovereigntyError):
    """Errors related to AI model loading, selection, or inference."""

    def __init__(self, message: str, model: str | None = None, details: dict | None = None):
        details = details or {}
        if model:
            details["model"] = model
        super().__init__(message, code="AI_MODEL_ERROR", details=details)


class WatcherError(SovereigntyError):
    """Errors related to watcher/listener operations."""

    def __init__(self, message: str, watcher: str | None = None, details: dict | None = None):
        details = details or {}
        if watcher:
            details["watcher"] = watcher
        super().__init__(message, code="WATCHER_ERROR", details=details)


class ValidationError(SovereigntyError):
    """Errors related to input validation."""

    def __init__(self, message: str, field: str | None = None, details: dict | None = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class ConfigurationError(SovereigntyError):
    """Errors related to configuration issues."""

    def __init__(self, message: str, config_key: str | None = None, details: dict | None = None):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, code="CONFIG_ERROR", details=details)


class NetworkError(SovereigntyError):
    """Errors related to network operations."""

    def __init__(self, message: str, url: str | None = None, details: dict | None = None):
        details = details or {}
        if url:
            details["url"] = url
        super().__init__(message, code="NETWORK_ERROR", details=details)


class TimeoutError(SovereigntyError):
    """Errors related to operation timeouts."""

    def __init__(self, message: str, timeout: float | None = None, details: dict | None = None):
        details = details or {}
        if timeout:
            details["timeout"] = timeout
        super().__init__(message, code="TIMEOUT_ERROR", details=details)
