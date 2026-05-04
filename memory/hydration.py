"""
memory/hydration.py
===================
Boot-time memory hydration for Sovereignty AI Studio.

Hydration is the process of loading persisted memories at startup and
injecting relevant context into each agent's working state.  Think of it
like warm-starting a conversation — agents "remember" prior interactions
rather than starting cold on every process restart.

How it works
------------
1. On boot, :meth:`MemoryHydration.hydrate` loads the most recent records
   from each registered namespace.
2. Each record is assembled into a compact "context block" — a human-readable
   text snippet that can be prepended to an agent's system prompt.
3. Callers request their context block via :meth:`MemoryHydration.get_context`,
   which returns a ready-to-use string.
4. New interactions can be persisted back via :meth:`MemoryHydration.record_interaction`
   so future sessions benefit from today's conversations.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from .memory_store import MemoryStore, MemoryRecord

log = logging.getLogger(__name__)

# Maximum number of prior interactions to inject per agent context block.
_MAX_CONTEXT_ENTRIES = 20

# Namespace used for storing interaction history per agent.
_INTERACTION_NS_PREFIX = "interactions"

# Namespace for global system-wide context (e.g. user preferences).
_GLOBAL_NS = "global"


class MemoryHydration:
    """Boot-time hydration engine that seeds agents with persistent context.

    Args:
        store: The :class:`~memory.memory_store.MemoryStore` to load from
               and persist to.  A default store is created if not provided.

    Example::

        hydration = MemoryHydration()
        await hydration.hydrate()

        # Inject context into a bridge agent's system prompt
        ctx = hydration.get_context("bridge")
        system_prompt = f"{base_prompt}\\n\\nPrior context:\\n{ctx}"

        # After receiving an AI response, persist it
        await hydration.record_interaction(
            agent="bridge",
            user_msg="What's the weather?",
            ai_reply="The weather service is at port 8001.",
        )
    """

    def __init__(self, store: Optional[MemoryStore] = None) -> None:
        self._store = store or MemoryStore(namespace=_GLOBAL_NS)
        # agent_id → list of context text snippets (newest last)
        self._context_cache: Dict[str, List[str]] = {}
        self._hydrated = False

    # ------------------------------------------------------------------
    # Hydration
    # ------------------------------------------------------------------

    async def hydrate(self, agent_ids: Optional[List[str]] = None) -> None:
        """Load persisted memories and build context caches.

        Call this once at process startup before any agents start receiving
        requests.

        Args:
            agent_ids: Specific agent IDs to hydrate.  When ``None`` the
                       method hydrates all namespaces currently in the store.
        """
        await self._store.initialise()
        log.info("MemoryHydration: starting boot hydration...")

        # Load global context (user preferences, system-wide facts)
        global_records = await self._store.load_namespace(
            _GLOBAL_NS, limit=50
        )
        global_snippets = [self._record_to_snippet(r) for r in global_records]
        self._context_cache["_global"] = global_snippets

        # Load per-agent interaction history
        targets = agent_ids or await self._list_interaction_namespaces()
        for agent_id in targets:
            ns = f"{_INTERACTION_NS_PREFIX}:{agent_id}"
            records = await self._store.load_namespace(
                ns, limit=_MAX_CONTEXT_ENTRIES
            )
            snippets = [self._record_to_snippet(r) for r in records]
            # Reverse so the most recent entry appears last (chronological order
            # feels natural when prepended to a system prompt)
            self._context_cache[agent_id] = list(reversed(snippets))
            log.debug(
                "Hydrated agent '%s' with %d memory entries", agent_id, len(snippets)
            )

        self._hydrated = True
        log.info(
            "MemoryHydration: complete — %d namespace(s) loaded",
            len(self._context_cache),
        )

    async def _list_interaction_namespaces(self) -> List[str]:
        """Return agent IDs inferred from existing interaction namespaces."""
        # We can't query distinct namespaces without a helper query — keep it
        # simple by checking known default agent IDs from the config.
        # Agents that have never had an interaction will get an empty context.
        return ["bridge", "judge", "ai_router", "platform", "voice", "plugin"]

    # ------------------------------------------------------------------
    # Context retrieval
    # ------------------------------------------------------------------

    def get_context(
        self,
        agent_id: str,
        *,
        max_entries: int = _MAX_CONTEXT_ENTRIES,
        include_global: bool = True,
    ) -> str:
        """Return a formatted context string ready to inject into a system prompt.

        Args:
            agent_id:       Agent whose history to include.
            max_entries:    Cap the number of prior interactions.
            include_global: Prepend global context (user prefs, system facts).

        Returns:
            Multi-line string summarising relevant prior context, or an empty
            string if no memory has been hydrated for this agent.
        """
        lines: List[str] = []

        if include_global:
            global_snippets = self._context_cache.get("_global", [])
            if global_snippets:
                lines.append("=== System Context ===")
                lines.extend(global_snippets[-max_entries:])

        agent_snippets = self._context_cache.get(agent_id, [])
        if agent_snippets:
            lines.append(f"=== Prior {agent_id} Interactions ===")
            lines.extend(agent_snippets[-max_entries:])

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Recording new interactions
    # ------------------------------------------------------------------

    async def record_interaction(
        self,
        agent: str,
        user_msg: str,
        ai_reply: str,
        *,
        extra_tags: Optional[List[str]] = None,
    ) -> None:
        """Persist an AI interaction so future sessions can learn from it.

        Args:
            agent:      Agent identifier (e.g. ``"bridge"``, ``"judge"``).
            user_msg:   The user's input message.
            ai_reply:   The AI's response text.
            extra_tags: Additional tags for search/filtering.
        """
        ns = f"{_INTERACTION_NS_PREFIX}:{agent}"
        key = f"interaction_{int(time.time() * 1000)}"
        payload: Dict[str, Any] = {
            "user": user_msg[:500],   # Truncate very long messages
            "ai": ai_reply[:500],
            "ts": time.time(),
        }
        tags = ["interaction", f"agent:{agent}"] + (extra_tags or [])

        record = await self._store.save(
            key, payload, namespace=ns, tags=tags
        )

        # Update the in-process cache so the context is immediately available
        snippet = self._record_to_snippet(record)
        if agent not in self._context_cache:
            self._context_cache[agent] = []
        self._context_cache[agent].append(snippet)

        # Keep the cache from growing unbounded
        if len(self._context_cache[agent]) > _MAX_CONTEXT_ENTRIES * 2:
            self._context_cache[agent] = self._context_cache[agent][
                -_MAX_CONTEXT_ENTRIES:
            ]

        log.debug("Recorded interaction for agent '%s'", agent)

    async def save_global(
        self,
        key: str,
        value: Any,
        *,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Persist a global fact or preference.

        Args:
            key:   Identifier (e.g. ``"user_theme"``, ``"preferred_model"``).
            value: JSON-serialisable value.
            tags:  Optional search tags.
        """
        record = await self._store.save(
            key, value, namespace=_GLOBAL_NS, tags=tags or ["global"]
        )
        snippet = self._record_to_snippet(record)
        if "_global" not in self._context_cache:
            self._context_cache["_global"] = []
        self._context_cache["_global"].append(snippet)
        log.debug("Saved global memory key '%s'", key)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_to_snippet(record: MemoryRecord) -> str:
        """Convert a MemoryRecord to a compact human-readable text snippet."""
        value = record.value
        if isinstance(value, dict):
            # Pretty-print interaction records
            if "user" in value and "ai" in value:
                return (
                    f"[{record.key}] User: {value['user'][:120]} "
                    f"→ AI: {value['ai'][:120]}"
                )
            return f"[{record.key}] {json.dumps(value, ensure_ascii=False)[:200]}"
        return f"[{record.key}] {str(value)[:200]}"
