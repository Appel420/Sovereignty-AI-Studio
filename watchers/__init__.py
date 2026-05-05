"""
Sovereignty AI Studio — Watchers Module

Provides async watchers, listeners, and event handlers:
  - BridgeWatcher: monitors WebSocket connection health
  - MemoryWatcher: watches for memory store changes and emits events
  - EventBus: in-process pub/sub for agent coordination
"""

from .bridge_watcher import BridgeWatcher
from .event_bus import EventBus
from .memory_watcher import MemoryWatcher

__all__ = ["BridgeWatcher", "EventBus", "MemoryWatcher"]
