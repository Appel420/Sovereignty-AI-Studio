"""
Sovereignty AI Studio — Persistent Memory System
=================================================
Provides persistent, searchable memory for the AI studio.

Exports:
    MemoryStore       — core save/load with JSON + SQLite hybrid backing
    MemoryHydration   — boot-time hydration that injects context into agents
    MemoryIndex       — recency + relevance scored searchable index

Typical usage::

    from memory import MemoryStore, MemoryHydration, MemoryIndex

    store = MemoryStore()
    await store.save("user_pref", {"theme": "dark"})
    record = await store.load("user_pref")
"""

from .memory_store import MemoryStore, MemoryRecord
from .hydration import MemoryHydration
from .memory_index import MemoryIndex

__all__ = [
    "MemoryStore",
    "MemoryRecord",
    "MemoryHydration",
    "MemoryIndex",
]
