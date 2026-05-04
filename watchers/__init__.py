"""
Sovereignty AI Studio — Watchers & Listeners
=============================================
Background monitoring services that run alongside the orchestrator.

Exports:
    FileWatcher     — watches config/model files and triggers hot-reload
    HealthWatcher   — polls service endpoints and reports health status
    EventListener   — central async event dispatcher to registered handlers

Typical usage::

    from watchers import FileWatcher, HealthWatcher, EventListener

    fw = FileWatcher(paths=["config.json"])
    hw = HealthWatcher()
    el = EventListener()
"""

from .file_watcher import FileWatcher, FileChangeEvent
from .health_watcher import HealthWatcher, ServiceHealth, HealthStatus
from .event_listener import EventListener, EventHandler

__all__ = [
    "FileWatcher",
    "FileChangeEvent",
    "HealthWatcher",
    "ServiceHealth",
    "HealthStatus",
    "EventListener",
    "EventHandler",
]
