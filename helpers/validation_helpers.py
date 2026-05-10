"""
Input validation and sanitization helpers.
"""

import re
from typing import Any

from errors.exceptions import ValidationError

# Valid message types for WebSocket communication
VALID_MESSAGE_TYPES = {
    "ai_chat",
    "ai_response",
    "ai_code_review",
    "ai_code_review_result",
    "memory_query",
    "memory_result",
    "memory_save",
    "memory_saved",
    "memory_get",
    "token_op",
    "token_result",
    "ping",
    "pong",
    "status",
    "status_response",
    "handshake_ack",
    "event_publish",
}

# Pattern for valid session IDs (alphanumeric, hyphens, underscores)
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Pattern for valid agent names
AGENT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")


def validate_message_type(msg_type: str) -> str:
    """
    Validate WebSocket message type.

    Args:
        msg_type: Message type to validate

    Returns:
        Validated message type

    Raises:
        ValidationError: If message type is invalid
    """
    if not isinstance(msg_type, str):
        raise ValidationError("Message type must be a string", field="type")

    if not msg_type:
        raise ValidationError("Message type cannot be empty", field="type")

    if msg_type not in VALID_MESSAGE_TYPES:
        raise ValidationError(
            f"Unknown message type: {msg_type}",
            field="type",
            details={"valid_types": list(VALID_MESSAGE_TYPES)},
        )

    return msg_type


def validate_session_id(session_id: str) -> str:
    """
    Validate session ID format.

    Args:
        session_id: Session ID to validate

    Returns:
        Validated session ID

    Raises:
        ValidationError: If session ID is invalid
    """
    if not isinstance(session_id, str):
        raise ValidationError("Session ID must be a string", field="session")

    if not session_id:
        raise ValidationError("Session ID cannot be empty", field="session")

    if not SESSION_ID_PATTERN.match(session_id):
        raise ValidationError(
            "Session ID must be 1-64 alphanumeric characters, hyphens, or underscores",
            field="session",
        )

    return session_id


def validate_agent_name(agent: str) -> str:
    """
    Validate agent name format.

    Args:
        agent: Agent name to validate

    Returns:
        Validated agent name

    Raises:
        ValidationError: If agent name is invalid
    """
    if not isinstance(agent, str):
        raise ValidationError("Agent name must be a string", field="agent")

    if not agent:
        raise ValidationError("Agent name cannot be empty", field="agent")

    if not AGENT_NAME_PATTERN.match(agent):
        raise ValidationError(
            "Agent name must be 1-32 alphanumeric characters, hyphens, or underscores",
            field="agent",
        )

    return agent


def sanitize_input(text: str, max_length: int = 100000) -> str:
    """
    Sanitize user input text.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text

    Raises:
        ValidationError: If input is invalid or too long
    """
    if not isinstance(text, str):
        raise ValidationError("Input must be a string")

    if len(text) > max_length:
        raise ValidationError(
            f"Input exceeds maximum length of {max_length} characters",
            details={"actual_length": len(text), "max_length": max_length},
        )

    # Remove null bytes and other control characters except newlines and tabs
    sanitized = text.replace("\x00", "")
    sanitized = "".join(
        char for char in sanitized if char == "\n" or char == "\t" or ord(char) >= 32
    )

    return sanitized
