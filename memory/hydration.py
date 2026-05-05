"""
MemoryHydrator — loads persisted memory into runtime state on startup.

Hydration means:
  1. Load saved agent configs from the KV store into memory.
  2. Replay recent conversation history into bridge context.
  3. Restore any cached API key metadata (not the keys themselves).
  4. Emit an 'sg:memoryHydrated' event for downstream consumers.

Usage:
    hydrator = MemoryHydrator(store)
    context = await hydrator.hydrate()
    # context is a dict ready to be broadcast to connected clients
"""

import asyncio
import json
import logging
import time
from typing import Any

from .store import MemoryStore

log = logging.getLogger("memory.hydration")


class MemoryHydrator:
    """Hydrates runtime memory from a MemoryStore on startup."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def hydrate(self, session: str = "default") -> dict[str, Any]:
        """
        Load persisted state and return a hydration payload dict.

        The returned dict can be broadcast to connected WebSocket clients
        so the front-end can restore its last state without a round-trip.
        """
        store = self._store

        # 1. Load agent config
        agent_cfg = await store.get("agent_config", {})

        # 2. Load recent conversation history
        history = await store.get_history(session, limit=40)

        # 3. Load cached key metadata (provider names only, not actual keys)
        key_meta = await store.get("api_key_meta", {})

        # 4. Load saved preferences
        prefs = await store.get("sg_prefs", {})

        # 5. Recent events for audit replay
        recent_events = await store.get_events(limit=20)

        # 6. KV snapshot (non-sensitive keys)
        kv_keys = await store.keys()
        kv_snap: dict[str, Any] = {}
        for k in kv_keys:
            if not any(skip in k for skip in ("secret", "key", "password", "token")):
                kv_snap[k] = await store.get(k)

        payload: dict[str, Any] = {
            "type": "memory_hydrated",
            "ts": int(time.time() * 1000),
            "session": session,
            "agent_config": agent_cfg,
            "history": history,
            "key_meta": key_meta,
            "prefs": prefs,
            "recent_events": recent_events,
            "kv": kv_snap,
        }

        log.info(
            "Hydrated session=%s: %d messages, %d kv keys",
            session,
            len(history),
            len(kv_snap),
        )

        await store.log_event("memory_hydrated", {"session": session, "msg_count": len(history)})
        return payload

    async def persist_message(
        self, session: str, role: str, content: str, agent: str = "system"
    ) -> None:
        """Convenience: save a message and trim history to 500 entries."""
        await self._store.add_message(session, role, content, agent)
        # Keep DB from growing unbounded — trim oldest beyond 500
        count = await self._store.count_messages(session)
        if count > 500:
            # SQLite doesn't support LIMIT in DELETE, use subquery
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store._exec,
                (
                    "DELETE FROM conversations WHERE id IN ("
                    "  SELECT id FROM conversations WHERE session=? "
                    "  ORDER BY ts ASC LIMIT ?"
                    ")"
                ),
                (session, count - 500),
            )

    async def save_agent_config(self, config: dict) -> None:
        """Persist agent configuration to the KV store."""
        await self._store.set("agent_config", config)

    async def save_prefs(self, prefs: dict) -> None:
        """Persist user preferences."""
        await self._store.set("sg_prefs", prefs)

    async def snapshot(self) -> dict[str, Any]:
        """Return a lightweight status snapshot (for health checks)."""
        kv_keys = await self._store.keys()
        events = await self._store.get_events(limit=5)
        return {
            "type": "memory_snapshot",
            "ts": int(time.time() * 1000),
            "kv_count": len(kv_keys),
            "recent_events": events,
        }
