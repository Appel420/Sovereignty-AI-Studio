"""
JSON serialization/deserialization helpers with error handling.
"""

import json
import logging
from typing import Any

from errors.exceptions import ValidationError

log = logging.getLogger("helpers.json")


def safe_json_loads(data: str, default: Any = None) -> Any:
    """
    Parse JSON string with error handling.

    Args:
        data: JSON string to parse
        default: Value to return if parsing fails

    Returns:
        Parsed JSON data or default value
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        log.warning("Failed to parse JSON: %s", e)
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Serialize object to JSON string with error handling.

    Args:
        obj: Object to serialize
        default: String to return if serialization fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as e:
        log.warning("Failed to serialize JSON: %s", e)
        return default


def json_to_dict(data: str | bytes) -> dict:
    """
    Convert JSON string or bytes to dictionary.

    Args:
        data: JSON data to convert

    Returns:
        Dictionary from JSON data

    Raises:
        ValidationError: If data is not valid JSON or not an object
    """
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValidationError(f"Expected JSON object, got {type(result).__name__}")
        return result
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
        raise ValidationError(f"Invalid JSON data: {e}") from e


def dict_to_json(data: dict, pretty: bool = False) -> str:
    """
    Convert dictionary to JSON string.

    Args:
        data: Dictionary to convert
        pretty: Whether to format with indentation

    Returns:
        JSON string

    Raises:
        ValidationError: If data cannot be serialized
    """
    try:
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Cannot serialize to JSON: {e}") from e
