# Helpers, Fixers, Listeners, and Error Handlers

This document describes the new infrastructure for error handling, utilities, self-healing, and event monitoring in Sovereignty AI Studio.

## Overview

The new infrastructure provides four key modules:

1. **Errors** - Comprehensive error handling with custom exceptions, retry logic, and circuit breakers
2. **Helpers** - Utility functions for common operations (JSON, validation, hashing, etc.)
3. **Fixers** - Self-healing and automatic recovery for connections, databases, configs, and models
4. **Watchers** - Enhanced listeners for AI model selection and medical AI workflows

## Errors Module

Located in `/errors/`, provides robust error handling infrastructure.

### Custom Exceptions

```python
from errors import (
    SovereigntyError,      # Base exception
    BridgeError,           # WebSocket bridge errors
    MemoryError,           # Memory store errors
    TokenError,            # Token management errors
    AIModelError,          # AI model errors
    WatcherError,          # Watcher/listener errors
    ValidationError,       # Input validation errors
    ConfigurationError,    # Configuration errors
    NetworkError,          # Network errors
    TimeoutError,          # Timeout errors
)
```

### Error Handlers

```python
from errors import ErrorHandler, RetryHandler, FallbackHandler, CircuitBreaker

# Basic error tracking
handler = ErrorHandler()
handler.handle(error, context="operation name")

# Retry with exponential backoff
retry_handler = RetryHandler(max_retries=3, base_delay=1.0)
result = await retry_handler.execute(async_function, context="retry operation")

# Fallback on error
fallback_handler = FallbackHandler(fallback="default value")
result = await fallback_handler.execute(async_function, context="fallback operation")

# Circuit breaker for failing services
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
result = await breaker.execute(async_function)
```

### Decorators

```python
from errors import handle_errors, retry_on_failure, fallback_on_error, log_errors

# Automatic retry
@retry_on_failure(max_retries=3, base_delay=1.0)
async def flaky_operation():
    # Will retry up to 3 times with exponential backoff
    pass

# Fallback value
@fallback_on_error(fallback="default")
async def operation_with_fallback():
    # Returns "default" if function raises exception
    pass

# Combined error handling
@handle_errors(retry=True, max_retries=3, fallback="default")
async def robust_operation():
    # Retries up to 3 times, then returns fallback if all fail
    pass
```

## Helpers Module

Located in `/helpers/`, provides utility functions for common operations.

### JSON Helpers

```python
from helpers import safe_json_loads, safe_json_dumps, json_to_dict, dict_to_json

# Safe JSON parsing (returns default on error)
data = safe_json_loads(json_string, default={})

# Safe JSON serialization
json_str = safe_json_dumps(data, default="{}")

# Strict JSON parsing (raises ValidationError on error)
data = json_to_dict(json_string)
```

### Message Helpers

```python
from helpers import format_ws_message, parse_ws_message, create_response, create_error_response

# Format WebSocket message
msg = format_ws_message("ai_chat", message="Hello", agent="claude")

# Parse WebSocket message
data = parse_ws_message(raw_message)

# Create response
response = create_response("ai_response", data={"text": "Hello"}, success=True)

# Create error response
error = create_error_response("error", "Something went wrong", code="ERR001")
```

### Hash Helpers

```python
from helpers import sha256, sha3_512, calculate_checksum, verify_checksum

# Calculate hashes
hash_val = sha256("data")
hash_val = sha3_512("data")

# Calculate and verify checksums
checksum = calculate_checksum(data, algorithm="sha256")
is_valid = verify_checksum(data, checksum, algorithm="sha256")
```

### Validation Helpers

```python
from helpers import validate_message_type, validate_session_id, validate_agent_name, sanitize_input

# Validate message type (raises ValidationError if invalid)
msg_type = validate_message_type("ai_chat")

# Validate session ID
session = validate_session_id("session-123")

# Validate agent name
agent = validate_agent_name("claude")

# Sanitize user input
clean_text = sanitize_input(user_input, max_length=10000)
```

### Time Helpers

```python
from helpers import current_timestamp_ms, format_timestamp, time_since

# Get current timestamp in milliseconds
ts = current_timestamp_ms()

# Format timestamp as human-readable string
formatted = format_timestamp(ts, fmt="%Y-%m-%d %H:%M:%S")

# Calculate elapsed time
elapsed = time_since(past_timestamp)
# Returns: {"days": 0, "hours": 1, "minutes": 30, "seconds": 45, "total_seconds": 5445}
```

### Path Helpers

```python
from helpers import ensure_dir, safe_path_join, get_data_dir, get_logs_dir

# Ensure directory exists
path = ensure_dir("/path/to/dir")

# Safely join paths (prevents directory traversal)
safe_path = safe_path_join(base_dir, "subdir", "file.txt")

# Get standard directories
data_dir = get_data_dir()
logs_dir = get_logs_dir()
```

## Fixers Module

Located in `/fixers/`, provides self-healing and automatic recovery.

### Connection Fixer

```python
from fixers import ConnectionFixer

fixer = ConnectionFixer(max_retries=5, retry_delay=2.0)

# Fix broken connection
success = await fixer.fix_connection(connect_func, test_func)

# Ensure connected with retry
await fixer.ensure_connected(connect_func, is_connected_func)

# Monitor connection health with auto-fix
await fixer.start_monitoring(health_check_func, fix_func)
```

### Database Fixer

```python
from fixers import DatabaseFixer

fixer = DatabaseFixer(db_path, schema)

# Check database integrity
is_healthy, issues = fixer.check_integrity()

# Create backup
backup_path = fixer.create_backup()

# Fix database issues (automatically rebuilds if corrupted)
success = await fixer.fix_database()

# Vacuum database to reclaim space
fixer.vacuum_database()
```

### Configuration Fixer

```python
from fixers import ConfigFixer

fixer = ConfigFixer()

# Validate configuration
is_valid, issues = fixer.validate_config(config)

# Fix invalid configuration with defaults
fixed_config = fixer.fix_config(config)

# Fix environment configuration
config = fixer.fix_env_config()

# Ensure config file exists with valid content
fixer.ensure_config_file(config_path)
```

### Model Fixer

```python
from fixers import ModelFixer

fixer = ModelFixer()

# Register fallback models
fixer.register_fallback("claude", "gpt-4")

# Get fallback for failed model
fallback = fixer.get_fallback_model("claude")

# Fix model selection (finds available alternative)
model = fixer.fix_model_selection("claude-3-opus", available_models)

# Mark model as failed
fixer.mark_model_failed("claude-3")

# Check if model has failed
if fixer.is_model_failed("claude-3"):
    # Use fallback

# Get model family (claude, gpt, grok, qwen, etc.)
family = fixer.get_model_family("claude-3-opus")  # Returns "claude"
```

### Health Monitor

```python
from fixers import HealthMonitor

monitor = HealthMonitor(check_interval=60.0, auto_fix=True)

# Register health checks with optional fixers
monitor.register_health_check("database", check_db_health, fix_db)
monitor.register_health_check("connection", check_conn_health, fix_conn)

# Start background monitoring
await monitor.start_monitoring()

# Check system health
is_healthy = monitor.is_healthy()

# Get detailed status
status = monitor.status()
```

## Watchers Module

Located in `/watchers/`, provides enhanced event listeners.

### AI Model Watcher

```python
from watchers import AIModelWatcher
from fixers import ModelFixer

model_fixer = ModelFixer()
watcher = AIModelWatcher(event_bus, model_fixer)

# Start watching AI model events
await watcher.start()

# Select appropriate model for request
model = watcher.select_model({"use_judge": True})

# Get model statistics
stats = watcher.get_model_stats("claude-3-opus")
# Returns: {"usage_count": 100, "error_count": 2, "error_rate": 0.02, "avg_latency_ms": 450}

# Get overall status
status = watcher.status()
```

### Medical AI Watcher

```python
from watchers import MedicalAIWatcher

watcher = MedicalAIWatcher(event_bus)

# Start watching medical AI events
await watcher.start()

# Get model performance metrics
performance = watcher.get_model_performance("medical-classifier-v1")

# Get HIPAA compliance summary
compliance = watcher.get_compliance_summary()
# Returns: {"hipaa_violations": 0, "compliance_rate": 1.0}

# Get overall status
status = watcher.status()
```

## Integration Examples

See `integration_example.py` for comprehensive examples of how to integrate all modules.

### Basic Error Handling

```python
from errors import handle_errors

@handle_errors(retry=True, max_retries=3, fallback="default response")
async def ai_chat(message: str) -> str:
    # Automatically retries on failure, returns fallback if all attempts fail
    response = await model.generate(message)
    return response
```

### WebSocket Message Handling

```python
from helpers import parse_ws_message, validate_message_type, create_response, create_error_response

async def handle_message(raw: str):
    try:
        msg = parse_ws_message(raw)
        msg_type = validate_message_type(msg["type"])

        # Process message...
        result = await process(msg)

        return create_response(msg_type + "_response", data=result)
    except Exception as e:
        return create_error_response("error", error=e)
```

### Auto-Recovery Setup

```python
from fixers import ConfigFixer, DatabaseFixer, HealthMonitor

async def setup_auto_recovery():
    # Fix configuration
    config_fixer = ConfigFixer()
    config = config_fixer.fix_env_config()

    # Fix database
    db_fixer = DatabaseFixer(db_path, schema)
    await db_fixer.fix_database()

    # Setup health monitoring
    monitor = HealthMonitor(auto_fix=True)
    monitor.register_health_check("db", check_db, fix_db)
    monitor.register_health_check("conn", check_conn, fix_conn)
    await monitor.start_monitoring()
```

## Testing

Tests are located in `/tests/`:

- `test_errors.py` - Tests for error handling
- `test_helpers.py` - Tests for helper functions
- `test_fixers.py` - Tests for fixers

Run tests with:
```bash
python3 -m pytest tests/test_errors.py -v
python3 -m pytest tests/test_helpers.py -v
python3 -m pytest tests/test_fixers.py -v
```

## Architecture

All modules follow these design principles:

1. **Async-first** - All operations use async/await for non-blocking execution
2. **Type hints** - Full type annotations for better IDE support and type checking
3. **Error handling** - Comprehensive error handling with custom exceptions
4. **Logging** - Detailed logging for debugging and monitoring
5. **Status reporting** - All components provide `.status()` method for introspection
6. **Graceful degradation** - Fallbacks and defaults for resilient operation

## Best Practices

1. **Always use decorators** for consistent error handling across functions
2. **Validate inputs early** using validation helpers
3. **Register health checks** for all critical components
4. **Use circuit breakers** for external service calls
5. **Enable auto-fix** in production for self-healing behavior
6. **Monitor statistics** using watcher status methods
7. **Test with pytest** to ensure proper error handling

## See Also

- `integration_example.py` - Comprehensive integration examples
- `bridge.py` - Main bridge server using some of these patterns
- `watchers/` - Existing watchers (bridge, memory) that follow similar patterns
