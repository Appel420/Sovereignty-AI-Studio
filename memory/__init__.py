"""
Sovereignty AI Studio — Persistent Memory Module

SQLite-backed memory store with hydration support.
Stores conversation history, agent context, and key-value pairs.
Exposes async API for use with asyncio (bridge.py, gateway).

Exports:
    MemoryStore       — async SQLite store (conversations, kv, events)
    MemoryHydrator    — boot-time hydration that injects context into bridge
    MemoryRecord      — dataclass for named memory entries
    MemoryHydration   — session-scoped hydration helper (legacy)
    MemoryIndex       — recency + relevance scored searchable index
"""

from .store import MemoryStore
from .hydration import MemoryHydrator
from .memory_store import MemoryRecord
from .memory_store import MemoryStore as _MemoryStoreLegacy  # alias for backward compat
from .hydration import MemoryHydrator as MemoryHydration  # legacy alias
from .memory_index import MemoryIndex

__all__ = [
    "MemoryStore",
    "MemoryHydrator",
    "MemoryRecord",
    "MemoryHydration",   # alias → MemoryHydrator (backward compat)
    "MemoryIndex",
]
