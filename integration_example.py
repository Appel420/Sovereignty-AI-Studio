"""
Integration example showing how to use errors, helpers, fixers, and watchers.

This module demonstrates best practices for integrating the new infrastructure
into existing code like bridge.py, memory modules, and watchers.
"""

import asyncio
import logging

# Import error handling
from errors import (
    BridgeError,
    MemoryError,
    AIModelError,
    handle_errors,
    retry_on_failure,
    fallback_on_error,
    RetryHandler,
    CircuitBreaker,
)

# Import helpers
from helpers import (
    format_ws_message,
    parse_ws_message,
    create_response,
    create_error_response,
    sha256,
    validate_message_type,
    validate_session_id,
    current_timestamp_ms,
)

# Import fixers
from fixers import (
    ConnectionFixer,
    DatabaseFixer,
    ConfigFixer,
    ModelFixer,
    HealthMonitor,
)

# Import watchers
from watchers import AIModelWatcher, MedicalAIWatcher

log = logging.getLogger("integration_example")


# Example 1: Error handling with decorators
@handle_errors(retry=True, max_retries=3, fallback="default response")
async def safe_ai_chat(message: str, agent: str) -> str:
    """
    Example AI chat function with automatic retry and fallback.
    """
    # This function will automatically retry up to 3 times
    # and return "default response" if all attempts fail
    response = await some_ai_model(message, agent)
    return response


# Example 2: Using helpers for message formatting
async def handle_websocket_message(raw_message: str):
    """
    Example WebSocket message handler using helpers.
    """
    try:
        # Parse message safely
        message = parse_ws_message(raw_message)

        # Validate message type
        msg_type = validate_message_type(message.get("type", ""))

        # Validate session
        session = validate_session_id(message.get("session", "default"))

        # Process message...
        result = {"status": "ok", "data": "processed"}

        # Create response
        response = create_response(
            msg_type + "_response",
            data=result,
            session=session,
        )

        return format_ws_message(response["type"], **response)

    except Exception as e:
        # Create error response
        error_response = create_error_response(
            "error",
            error=e,
            code=e.code if hasattr(e, "code") else "UNKNOWN",
        )
        return format_ws_message("error", **error_response)


# Example 3: Using fixers for auto-recovery
async def initialize_with_fixers():
    """
    Example initialization with automatic fixing.
    """
    # Initialize config fixer
    config_fixer = ConfigFixer()
    config = config_fixer.fix_env_config()
    log.info("Configuration fixed: %s", config)

    # Initialize database fixer
    from pathlib import Path
    db_path = Path("data/memory/memory.db")
    schema = "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY);"
    db_fixer = DatabaseFixer(db_path, schema)

    # Check and fix database
    is_healthy = await db_fixer.fix_database()
    if is_healthy:
        log.info("Database is healthy")
    else:
        log.error("Database could not be fixed")

    # Initialize model fixer
    model_fixer = ModelFixer()
    model_fixer.register_fallback("claude", "gpt-4")

    # Fix model selection
    try:
        model = model_fixer.fix_model_selection(
            "claude-3-opus",
            available_models=["gpt-4", "gpt-3.5-turbo"],
        )
        log.info("Selected model: %s", model)
    except AIModelError as e:
        log.error("Could not select model: %s", e)


# Example 4: Circuit breaker for failing services
async def call_with_circuit_breaker(url: str):
    """
    Example service call with circuit breaker.
    """
    breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60.0,
    )

    async def make_request():
        # Simulated HTTP request
        await asyncio.sleep(0.1)
        return "response"

    try:
        result = await breaker.execute(make_request)
        return result
    except Exception as e:
        log.error("Circuit breaker opened: %s", e)
        return None


# Example 5: Health monitoring
async def setup_health_monitoring():
    """
    Example health monitoring setup.
    """
    monitor = HealthMonitor(check_interval=30.0, auto_fix=True)

    # Register health checks
    async def check_database_health() -> bool:
        # Check if database is accessible
        return True

    async def check_connection_health() -> bool:
        # Check if connections are healthy
        return True

    async def fix_database():
        log.info("Fixing database...")
        # Implement fix logic

    async def fix_connection():
        log.info("Fixing connection...")
        # Implement fix logic

    monitor.register_health_check("database", check_database_health, fix_database)
    monitor.register_health_check("connection", check_connection_health, fix_connection)

    # Start monitoring
    await monitor.start_monitoring()

    # Monitor runs in background...
    # Later: await monitor.stop_monitoring()


# Example 6: Using AI model watcher
async def setup_ai_model_watcher(bus):
    """
    Example AI model watcher setup.
    """
    from fixers import ModelFixer

    model_fixer = ModelFixer()
    watcher = AIModelWatcher(bus, model_fixer)

    await watcher.start()

    # Watcher now monitors all AI events...
    # Get statistics
    stats = watcher.status()
    log.info("AI model stats: %s", stats)


# Example 7: Using medical AI watcher
async def setup_medical_ai_watcher(bus):
    """
    Example medical AI watcher setup.
    """
    watcher = MedicalAIWatcher(bus)

    await watcher.start()

    # Simulate medical workflow events
    await bus.publish("medical_training_start", {
        "model": "medical-classifier-v1",
        "dataset": "chest-xray",
    })

    await bus.publish("medical_training_complete", {
        "model": "medical-classifier-v1",
        "accuracy": 0.95,
        "f1_score": 0.93,
        "training_time_ms": 120000,
    })

    # Get compliance summary
    compliance = watcher.get_compliance_summary()
    log.info("Medical AI compliance: %s", compliance)


# Dummy function for example
async def some_ai_model(message: str, agent: str) -> str:
    """Dummy AI model function."""
    await asyncio.sleep(0.1)
    return f"Response from {agent}: {message}"


if __name__ == "__main__":
    # Run examples
    logging.basicConfig(level=logging.INFO)

    async def main():
        log.info("Running integration examples...")

        # Example 1: Error handling
        result = await safe_ai_chat("Hello", "claude")
        log.info("Result: %s", result)

        # Example 3: Fixers
        await initialize_with_fixers()

        log.info("Integration examples complete")

    asyncio.run(main())
