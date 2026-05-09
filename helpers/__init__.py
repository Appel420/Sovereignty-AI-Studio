"""
Sovereignty AI Studio — Helpers Module

Provides utility functions and helpers for common operations:
  - JSON and data serialization/deserialization
  - WebSocket message formatting
  - Hash and checksum utilities
  - Validation helpers
  - Time and timestamp utilities
  - Path and file helpers
"""

from .json_helpers import (
    safe_json_loads,
    safe_json_dumps,
    json_to_dict,
    dict_to_json,
)
from .message_helpers import (
    format_ws_message,
    parse_ws_message,
    create_response,
    create_error_response,
)
from .hash_helpers import (
    sha256,
    sha3_512,
    calculate_checksum,
    verify_checksum,
)
from .validation_helpers import (
    validate_message_type,
    validate_session_id,
    validate_agent_name,
    sanitize_input,
)
from .time_helpers import (
    current_timestamp_ms,
    format_timestamp,
    parse_timestamp,
    time_since,
)
from .path_helpers import (
    ensure_dir,
    safe_path_join,
    get_data_dir,
    get_logs_dir,
)

__all__ = [
    # JSON helpers
    "safe_json_loads",
    "safe_json_dumps",
    "json_to_dict",
    "dict_to_json",
    # Message helpers
    "format_ws_message",
    "parse_ws_message",
    "create_response",
    "create_error_response",
    # Hash helpers
    "sha256",
    "sha3_512",
    "calculate_checksum",
    "verify_checksum",
    # Validation helpers
    "validate_message_type",
    "validate_session_id",
    "validate_agent_name",
    "sanitize_input",
    # Time helpers
    "current_timestamp_ms",
    "format_timestamp",
    "parse_timestamp",
    "time_since",
    # Path helpers
    "ensure_dir",
    "safe_path_join",
    "get_data_dir",
    "get_logs_dir",
]
