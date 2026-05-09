"""
WebSocket message formatting and parsing helpers.
"""

import time
from typing import Any

from .json_helpers import safe_json_dumps, json_to_dict
from .time_helpers import current_timestamp_ms


def format_ws_message(msg_type: str, **kwargs: Any) -> str:
    """
    Format a WebSocket message with consistent structure.

    Args:
        msg_type: Message type identifier
        **kwargs: Additional message fields

    Returns:
        JSON-formatted message string
    """
    message = {
        "type": msg_type,
        "ts": current_timestamp_ms(),
        **kwargs,
    }
    return safe_json_dumps(message)


def parse_ws_message(raw: str | bytes) -> dict:
    """
    Parse a WebSocket message from raw data.

    Args:
        raw: Raw message data (string or bytes)

    Returns:
        Parsed message dictionary

    Raises:
        ValidationError: If message is invalid JSON
    """
    return json_to_dict(raw)


def create_response(
    msg_type: str,
    data: Any = None,
    success: bool = True,
    **kwargs: Any,
) -> dict:
    """
    Create a standardized response message.

    Args:
        msg_type: Response message type
        data: Response data payload
        success: Whether the operation was successful
        **kwargs: Additional response fields

    Returns:
        Response message dictionary
    """
    response = {
        "type": msg_type,
        "success": success,
        "ts": current_timestamp_ms(),
    }

    if data is not None:
        response["data"] = data

    response.update(kwargs)
    return response


def create_error_response(
    msg_type: str,
    error: str | Exception,
    code: str = "ERROR",
    **kwargs: Any,
) -> dict:
    """
    Create a standardized error response message.

    Args:
        msg_type: Response message type
        error: Error message or exception
        code: Error code identifier
        **kwargs: Additional error fields

    Returns:
        Error response message dictionary
    """
    error_msg = str(error)
    response = {
        "type": msg_type,
        "success": False,
        "error": error_msg,
        "error_code": code,
        "ts": current_timestamp_ms(),
    }

    # Include exception details if available
    if hasattr(error, "details"):
        response["error_details"] = error.details  # type: ignore

    response.update(kwargs)
    return response
