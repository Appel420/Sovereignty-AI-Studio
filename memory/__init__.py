"""
Sovereignty AI Studio — Persistent Memory Module

SQLite-backed memory store with hydration support.
Stores conversation history, agent context, and key-value pairs.
Exposes async API for use with asyncio (bridge.py, gateway).
"""

from .store import MemoryStore
from .hydration import MemoryHydrator

__all__ = ["MemoryStore", "MemoryHydrator"]
