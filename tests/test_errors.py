"""
Tests for error handling module.
"""

import asyncio
import pytest

from errors.exceptions import (
    SovereigntyError,
    BridgeError,
    MemoryError,
    AIModelError,
    ValidationError,
)
from errors.handlers import ErrorHandler, RetryHandler, FallbackHandler, CircuitBreaker
from errors.decorators import handle_errors, retry_on_failure, fallback_on_error


class TestExceptions:
    """Test custom exceptions."""

    def test_sovereignty_error(self):
        error = SovereigntyError("test error", code="TEST", details={"key": "value"})
        assert error.message == "test error"
        assert error.code == "TEST"
        assert error.details == {"key": "value"}
        assert "[TEST]" in str(error)

    def test_bridge_error(self):
        error = BridgeError("connection failed")
        assert error.code == "BRIDGE_ERROR"
        assert "connection failed" in str(error)

    def test_memory_error(self):
        error = MemoryError("database locked")
        assert error.code == "MEMORY_ERROR"

    def test_ai_model_error(self):
        error = AIModelError("model not found", model="claude-3")
        assert error.code == "AI_MODEL_ERROR"
        assert error.details["model"] == "claude-3"

    def test_validation_error(self):
        error = ValidationError("invalid input", field="email")
        assert error.code == "VALIDATION_ERROR"
        assert error.details["field"] == "email"


class TestErrorHandler:
    """Test error handler."""

    def test_error_handler_tracking(self):
        handler = ErrorHandler()
        assert handler.error_count == 0

        error = Exception("test error")
        handler.handle(error, context="test")
        assert handler.error_count == 1
        assert handler.last_error == error

    def test_error_handler_reset(self):
        handler = ErrorHandler()
        handler.handle(Exception("test"), context="test")
        handler.reset()
        assert handler.error_count == 0
        assert handler.last_error is None


class TestRetryHandler:
    """Test retry handler."""

    @pytest.mark.asyncio
    async def test_retry_success(self):
        handler = RetryHandler(max_retries=3)
        call_count = 0

        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("temporary error")
            return "success"

        result = await handler.execute(flaky_function, context="test")
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_failure(self):
        handler = RetryHandler(max_retries=2, base_delay=0.01)

        async def always_fails():
            raise Exception("permanent error")

        with pytest.raises(Exception, match="permanent error"):
            await handler.execute(always_fails, context="test")


class TestFallbackHandler:
    """Test fallback handler."""

    @pytest.mark.asyncio
    async def test_fallback_value(self):
        handler = FallbackHandler(fallback="default")

        async def failing_function():
            raise Exception("error")

        result = await handler.execute(failing_function, context="test")
        assert result == "default"

    @pytest.mark.asyncio
    async def test_fallback_function(self):
        handler = FallbackHandler(fallback=lambda: "computed default")

        async def failing_function():
            raise Exception("error")

        result = await handler.execute(failing_function, context="test")
        assert result == "computed default"


class TestCircuitBreaker:
    """Test circuit breaker."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        async def failing_function():
            raise Exception("service unavailable")

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute(failing_function)

        # Circuit should be open now
        assert breaker.state == "OPEN"

        # Next call should fail fast
        from errors.exceptions import TimeoutError

        with pytest.raises(TimeoutError):
            await breaker.execute(failing_function)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        call_count = 0

        async def recovering_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("temporary error")
            return "success"

        # Trigger failures
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.execute(recovering_function)

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Circuit should be half-open, next success closes it
        result = await breaker.execute(recovering_function)
        assert result == "success"
        assert breaker.state == "CLOSED"


class TestDecorators:
    """Test error handling decorators."""

    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        call_count = 0

        @retry_on_failure(max_retries=3, base_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("temporary error")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_fallback_decorator(self):
        @fallback_on_error(fallback="default value")
        async def failing_function():
            raise Exception("error")

        result = await failing_function()
        assert result == "default value"

    @pytest.mark.asyncio
    async def test_handle_errors_decorator(self):
        @handle_errors(retry=True, max_retries=2, fallback="fallback", reraise=False)
        async def failing_function():
            raise Exception("error")

        result = await failing_function()
        assert result == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
