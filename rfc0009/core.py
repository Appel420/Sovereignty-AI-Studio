"""Shared RFC-0009 validation definitions."""


class ValidationError(ValueError):
    """Raised when an RFC-0009 authority boundary rejects input."""


SUCCESS_TERMINAL = "SUCCESS"
TERMINAL_STATES = frozenset(
    {
        SUCCESS_TERMINAL,
        "FAILED",
        "REJECTED",
        "CANCELLED",
        "INCOMPLETE",
    }
)
