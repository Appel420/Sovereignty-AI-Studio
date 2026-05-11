"""
Time and timestamp utility functions.
"""

import time
from datetime import datetime, timezone


def current_timestamp_ms() -> int:
    """
    Get current timestamp in milliseconds.

    Returns:
        Current Unix timestamp in milliseconds
    """
    return int(time.time() * 1000)


def format_timestamp(timestamp_ms: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format timestamp (milliseconds) as human-readable string.

    Args:
        timestamp_ms: Unix timestamp in milliseconds
        fmt: strftime format string

    Returns:
        Formatted timestamp string
    """
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt.strftime(fmt)


def parse_timestamp(timestamp_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> int:
    """
    Parse timestamp string to milliseconds.

    Args:
        timestamp_str: Timestamp string to parse
        fmt: strptime format string

    Returns:
        Unix timestamp in milliseconds
    """
    dt = datetime.strptime(timestamp_str, fmt)
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def time_since(timestamp_ms: int) -> dict:
    """
    Calculate time elapsed since given timestamp.

    Args:
        timestamp_ms: Unix timestamp in milliseconds

    Returns:
        Dictionary with days, hours, minutes, seconds components
    """
    elapsed_seconds = (current_timestamp_ms() - timestamp_ms) / 1000

    days = int(elapsed_seconds // 86400)
    hours = int((elapsed_seconds % 86400) // 3600)
    minutes = int((elapsed_seconds % 3600) // 60)
    seconds = int(elapsed_seconds % 60)

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "total_seconds": int(elapsed_seconds),
    }
