# Sovereignty AI Studio — Plugin SDK

Build custom agents and tools that integrate with the Sovereignty AI Studio platform.

## Quick Start

```python
from plugins.sdk.plugin_base import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    display_name = "My Plugin"
    version = "1.0.0"
    description = "Does something useful"
    author = "Your Name"
    category = "utilities"

    def configure(self, config: dict) -> None:
        self.greeting = config.get("greeting", "Hello")

    def run(self, payload: dict) -> dict:
        name = payload.get("name", "World")
        return {"message": f"{self.greeting}, {name}!"}

    def health_check(self) -> bool:
        return True
```

## Plugin Entry Point

Register your plugin using the marketplace API:

```bash
POST /api/v1/marketplace/install
{
  "name": "my_plugin",
  "display_name": "My Plugin",
  "version": "1.0.0",
  "entry_point": "plugins.examples.my_plugin:MyPlugin",
  "category": "utilities"
}
```

Then activate it:

```bash
POST /api/v1/marketplace/my_plugin/activate
{"config": {"greeting": "Greetings"}}
```

## Plugin Lifecycle

1. **Install** — Registers the plugin in the database (status: `inactive`)
2. **Activate** — Imports the class, calls `configure()` then `start()` (status: `active`)
3. **Run** — Calls `run(payload)` for each request
4. **Health Check** — Platform periodically calls `health_check()` to monitor status
5. **Deactivate** — Calls `stop()`, releases resources (status: `inactive`)
6. **Uninstall** — Removes from database

## Required Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `run` | `(payload: dict) -> Any` | Primary action handler |
| `configure` | `(config: dict) -> None` | Apply runtime configuration |
| `health_check` | `() -> bool` | Return True if healthy |

## Optional Lifecycle Hooks

| Method | When Called |
|--------|-------------|
| `start()` | On activation — initialize connections, load models |
| `stop()` | On deactivation — release resources, close connections |

## Config Access

```python
def configure(self, config: dict) -> None:
    # Use self.get_config() helper with defaults
    self.api_key = self.get_config("api_key", "")
    self.timeout = self.get_config("timeout", 30)
```

## Logging

Each plugin gets its own logger automatically:

```python
self.logger.info("Processing request")
self.logger.warning("Falling back to default")
self.logger.error("Something went wrong: %s", error)
```

## Event Bus Integration

Plugins can publish events to the sovereign event bus:

```python
from app.services.event_bus import event_bus, Event

async def run(self, payload: dict) -> dict:
    result = self._process(payload)
    await event_bus.publish(Event(
        topic="plugin.result",
        payload=result,
        source=self.name,
    ))
    return result
```

## Example Plugins

See `plugins/examples/example_chat_plugin.py` for a complete working example.
