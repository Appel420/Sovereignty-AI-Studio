"""
Sovereignty AI Studio — Watchers Module

Provides async watchers, listeners, and event handlers for the orchestrator.

WebSocket / health monitoring:
  - BridgeWatcher: monitors WebSocket connection health
  - MemoryWatcher: watches for memory store changes and emits events
  - EventBus: in-process pub/sub for agent coordination

AI-specific watchers:
  - AIModelWatcher: monitors AI model selection and routing
  - MedicalAIWatcher: monitors medical AI workflows and compliance

Infrastructure watchers (background orchestrator services):
  - FileWatcher: polls config/model files and triggers hot-reload callbacks
  - HealthWatcher: polls HTTP endpoints and reports service health status
  - EventListener: central async fan-out dispatcher with DLQ
"""

from .bridge_watcher import BridgeWatcher
from .event_bus import EventBus
from .memory_watcher import MemoryWatcher
from .ai_model_watcher import AIModelWatcher
from .medical_ai_watcher import MedicalAIWatcher
from .file_watcher import FileWatcher, FileChangeEvent
from .health_watcher import HealthWatcher, ServiceHealth, HealthStatus
from .event_listener import EventListener, EventHandler

__all__ = [
    # Core watchers (used by bridge.py / gateway)
    "BridgeWatcher",
    "EventBus",
    "MemoryWatcher",
    "AIModelWatcher",
    "MedicalAIWatcher",
    # Infrastructure watchers (used by System_Orchestrator)
    "FileWatcher",
    "FileChangeEvent",
    "HealthWatcher",
    "ServiceHealth",
    "HealthStatus",
    "EventListener",
    "EventHandler",
]
