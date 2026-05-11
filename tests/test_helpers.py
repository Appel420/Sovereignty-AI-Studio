"""
Tests for helpers module.
"""

import pytest

from helpers.json_helpers import (
    safe_json_loads,
    safe_json_dumps,
    json_to_dict,
    dict_to_json,
)
from helpers.message_helpers import (
    format_ws_message,
    parse_ws_message,
    create_response,
    create_error_response,
)
from helpers.hash_helpers import sha256, sha3_512, calculate_checksum, verify_checksum
from helpers.validation_helpers import (
    validate_message_type,
    validate_session_id,
    validate_agent_name,
    sanitize_input,
)
from helpers.time_helpers import current_timestamp_ms, format_timestamp, time_since
from errors.exceptions import ValidationError


class TestJSONHelpers:
    """Test JSON helper functions."""

    def test_safe_json_loads_valid(self):
        result = safe_json_loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_safe_json_loads_invalid(self):
        result = safe_json_loads("invalid json", default={"error": True})
        assert result == {"error": True}

    def test_safe_json_dumps_valid(self):
        result = safe_json_dumps({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_json_to_dict_valid(self):
        result = json_to_dict('{"test": "data"}')
        assert result == {"test": "data"}

    def test_json_to_dict_invalid(self):
        with pytest.raises(ValidationError):
            json_to_dict("not json")

    def test_dict_to_json(self):
        result = dict_to_json({"test": "data"})
        assert isinstance(result, str)
        assert "test" in result


class TestMessageHelpers:
    """Test WebSocket message helpers."""

    def test_format_ws_message(self):
        msg = format_ws_message("test_type", data="test data")
        assert isinstance(msg, str)
        assert "test_type" in msg
        assert "test data" in msg

    def test_parse_ws_message(self):
        msg = '{"type": "test", "data": "value"}'
        result = parse_ws_message(msg)
        assert result["type"] == "test"
        assert result["data"] == "value"

    def test_create_response(self):
        response = create_response("test_response", data={"key": "value"})
        assert response["type"] == "test_response"
        assert response["success"] is True
        assert response["data"] == {"key": "value"}
        assert "ts" in response

    def test_create_error_response(self):
        response = create_error_response("error", "Something went wrong", code="ERR001")
        assert response["type"] == "error"
        assert response["success"] is False
        assert response["error"] == "Something went wrong"
        assert response["error_code"] == "ERR001"


class TestHashHelpers:
    """Test hash helper functions."""

    def test_sha256(self):
        result = sha256("test data")
        assert len(result) == 64  # SHA-256 produces 64 hex characters
        assert result == sha256("test data")  # Consistent

    def test_sha3_512(self):
        result = sha3_512("test data")
        assert len(result) == 128  # SHA3-512 produces 128 hex characters
        assert result == sha3_512("test data")  # Consistent

    def test_calculate_checksum(self):
        data = "test data"
        checksum = calculate_checksum(data, algorithm="sha256")
        assert len(checksum) == 64

    def test_verify_checksum(self):
        data = "test data"
        checksum = calculate_checksum(data, algorithm="sha256")
        assert verify_checksum(data, checksum, algorithm="sha256") is True
        assert verify_checksum(data, "invalid", algorithm="sha256") is False


class TestValidationHelpers:
    """Test validation helper functions."""

    def test_validate_message_type_valid(self):
        result = validate_message_type("ai_chat")
        assert result == "ai_chat"

    def test_validate_message_type_invalid(self):
        with pytest.raises(ValidationError):
            validate_message_type("invalid_type")

    def test_validate_session_id_valid(self):
        result = validate_session_id("session-123")
        assert result == "session-123"

    def test_validate_session_id_invalid(self):
        with pytest.raises(ValidationError):
            validate_session_id("")

        with pytest.raises(ValidationError):
            validate_session_id("invalid@session")

    def test_validate_agent_name_valid(self):
        result = validate_agent_name("claude")
        assert result == "claude"

    def test_validate_agent_name_invalid(self):
        with pytest.raises(ValidationError):
            validate_agent_name("")

        with pytest.raises(ValidationError):
            validate_agent_name("invalid agent name with spaces")

    def test_sanitize_input(self):
        # Test normal input
        result = sanitize_input("Hello world")
        assert result == "Hello world"

        # Test input with null bytes
        result = sanitize_input("Hello\x00world")
        assert result == "Helloworld"

        # Test input too long
        with pytest.raises(ValidationError):
            sanitize_input("x" * 100001)


class TestTimeHelpers:
    """Test time helper functions."""

    def test_current_timestamp_ms(self):
        ts = current_timestamp_ms()
        assert isinstance(ts, int)
        assert ts > 0

    def test_format_timestamp(self):
        ts = 1609459200000  # 2021-01-01 00:00:00 UTC
        formatted = format_timestamp(ts)
        assert "2021" in formatted
        assert "01" in formatted

    def test_time_since(self):
        import time

        past_ts = int((time.time() - 100) * 1000)
        elapsed = time_since(past_ts)

        assert elapsed["total_seconds"] >= 100
        assert elapsed["minutes"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
