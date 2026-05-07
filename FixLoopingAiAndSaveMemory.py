#!/usr/bin/env python3
"""
FixLoopingAiAndSaveMemory — Sovereignty AI Studio
==================================================
Prevents AI response loops and persists every conversation turn to the
SQLite-backed MemoryStore so context is never lost across restarts.

Key features
------------
1. Conversation memory   — rolling in-process history + SQLite persistence.
2. Context summary       — condensed rolling summary injected into every prompt
                           so the model always knows where the conversation stands.
3. Similarity-based loop detection — uses difflib.SequenceMatcher to catch
                           near-duplicate responses (not just exact matches).
4. Automatic reframing   — when a loop is detected the prompt is reframed and
                           the AI is asked to try a different angle.
5. Sovereign AI routing  — routes through SovereignBridge (local GGUF/ONNX)
                           with an HTTP fallback, exactly like bridge.py does.
                           No data ever leaves self-hosted infrastructure.

Usage
-----
    # Interactive CLI (sync wrapper):
    python3 FixLoopingAiAndSaveMemory.py

    # Async library usage:
    from FixLoopingAiAndSaveMemory import AIAssistant
    import asyncio

    async def main():
        ai = AIAssistant(session="my-session")
        await ai.init()
        reply = await ai.process_user_input("What is sovereignty?")
        print(reply)

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import os
import sys
import time
import urllib.request
from typing import Any

log = logging.getLogger("fix_loop_memory")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ---------------------------------------------------------------------------
# Configuration (mirrors bridge.py env-var conventions)
# ---------------------------------------------------------------------------
SOVEREIGN_API_URL = os.environ.get(
    "SOVEREIGN_API_URL", "http://localhost:9899/api/ai"
).rstrip("/")

# Similarity threshold: responses more similar than this trigger reframing.
LOOP_SIMILARITY_THRESHOLD = float(os.environ.get("LOOP_SIMILARITY_THRESHOLD", "0.85"))

# How many recent turns to consider when checking for loops.
LOOP_LOOKBACK = int(os.environ.get("LOOP_LOOKBACK", "4"))

# How many recent turns to include in the context summary sent to the model.
SUMMARY_LOOKBACK = int(os.environ.get("SUMMARY_LOOKBACK", "6"))

# Max conversation turns kept in the in-memory list (memory.store is unbounded).
MAX_IN_MEMORY_TURNS = int(os.environ.get("MAX_IN_MEMORY_TURNS", "100"))

# Max characters of the previous response shown in a reframe notice.
REFRAME_PREVIEW_LENGTH = 300


# ---------------------------------------------------------------------------
# Optional: persistent memory store
# ---------------------------------------------------------------------------

def _try_import_memory():
    try:
        from memory.store import MemoryStore
        from memory.hydration import MemoryHydrator
        return MemoryStore, MemoryHydrator
    except ImportError as exc:
        log.warning("memory module not available (persistence disabled): %s", exc)
        return None, None


# ---------------------------------------------------------------------------
# AI routing — mirrors the sovereign routing in bridge.py
# ---------------------------------------------------------------------------

def _chat_sovereign_sync(messages: list[dict], agent: str = "assistant") -> str:
    """Try SovereignBridge first, fall back to HTTP sovereign API."""
    try:
        from ai_core.sovereign_bridge import SovereignBridge
        bridge = SovereignBridge()
        return bridge.chat(messages)
    except Exception as exc:  # noqa: BLE001
        log.warning("SovereignBridge failed, using HTTP fallback: %s", exc)

    try:
        body = json.dumps({
            "messages": messages,
            "max_tokens": 2048,
            "context": {"agent": agent},
        }).encode()
        req = urllib.request.Request(
            f"{SOVEREIGN_API_URL}/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return (
                data.get("text")
                or data.get("response")
                or (data.get("choices", [{}])[0].get("message", {}).get("content", ""))
                or "[no response]"
            )
    except Exception as exc:  # noqa: BLE001
        log.error("Sovereign HTTP API error: %s", exc)
        return f"[Sovereign bridge error: {exc}]"


async def _chat_sovereign(messages: list[dict], agent: str = "assistant") -> str:
    """Async wrapper around the synchronous sovereign routing call."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _chat_sovereign_sync, messages, agent)


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class AIAssistant:
    """
    Sovereign AI assistant with loop detection and persistent memory.

    Parameters
    ----------
    session : str
        Conversation session identifier used for MemoryStore persistence.
    agent : str
        Agent name/label forwarded to the AI provider.
    """

    def __init__(self, session: str = "default", agent: str = "sovereign") -> None:
        self.session = session
        self.agent = agent

        # In-memory ring buffer of (user_input, ai_response) tuples.
        self._history: list[tuple[str, str]] = []

        # Rolling plain-text summary injected into each prompt.
        self.context_summary: str = ""

        # Persistent store (may be None if memory module is unavailable).
        store_cls, hydrator_cls = _try_import_memory()
        self._store = store_cls() if store_cls else None
        self._hydrator = hydrator_cls(self._store) if (hydrator_cls and self._store) else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Initialise the persistent memory store (idempotent)."""
        if self._store:
            try:
                await self._store.init()
                log.info("MemoryStore initialised for session=%s", self.session)
            except Exception as exc:
                log.warning("MemoryStore init failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_user_input(self, user_input: str) -> str:
        """
        Process one turn of conversation.

        Steps
        -----
        1. Update rolling context summary.
        2. Ask the sovereign AI (with context injected into the system prompt).
        3. Detect loops — if the response is too similar to recent replies,
           reframe the prompt and retry once.
        4. Save the turn to in-memory history and to the persistent store.
        5. Return the final reply.
        """
        # 1. Refresh context summary before building the prompt.
        self._update_context_summary(user_input)

        # 2. Build messages and get AI response.
        messages = self._build_messages(user_input)
        ai_response = await _chat_sovereign(messages, self.agent)

        # 3. Loop detection — retry with reframed prompt if needed.
        if self._detect_loop(ai_response):
            log.info("Loop detected; reframing prompt for session=%s", self.session)
            reframed_messages = self._build_messages(
                user_input, reframe=True, previous_response=ai_response
            )
            ai_response = await _chat_sovereign(reframed_messages, self.agent)

        # 4. Persist the turn.
        self._history.append((user_input, ai_response))
        if len(self._history) > MAX_IN_MEMORY_TURNS:
            self._history = self._history[-MAX_IN_MEMORY_TURNS:]

        await self._persist(user_input, ai_response)

        return ai_response

    # ------------------------------------------------------------------
    # Context summary
    # ------------------------------------------------------------------

    def _update_context_summary(self, incoming_user_input: str) -> None:
        """
        Rebuild a concise rolling summary from the last SUMMARY_LOOKBACK turns.

        The summary is plain text and is injected into the system prompt so the
        model always has recent context — even if the token window would otherwise
        cause it to forget earlier turns.
        """
        recent = self._history[-SUMMARY_LOOKBACK:]
        lines = [f"User: {u}\nAI: {a}" for u, a in recent]
        if lines:
            self.context_summary = "Recent conversation:\n" + "\n---\n".join(lines)
        else:
            self.context_summary = "(No prior conversation in this session.)"

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_input: str,
        *,
        reframe: bool = False,
        previous_response: str = "",
    ) -> list[dict[str, str]]:
        """Build an OpenAI-style message list for the sovereign bridge."""
        system_parts = [
            "You are a sovereign AI assistant running entirely on self-hosted infrastructure. "
            "No data leaves the network. Be precise, production-ready, and never fabricate data.",
            "",
            self.context_summary,
        ]

        if reframe:
            system_parts += [
                "",
                "IMPORTANT: Your previous response may have been repetitive. "
                "Approach this from a completely different angle. "
                f"Previous attempt: {previous_response[:REFRAME_PREVIEW_LENGTH]}",
            ]

        system_prompt = "\n".join(system_parts).strip()
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

    # ------------------------------------------------------------------
    # Loop detection
    # ------------------------------------------------------------------

    def _detect_loop(self, response: str) -> bool:
        """
        Return True if `response` is suspiciously similar to any of the last
        LOOP_LOOKBACK AI responses, using difflib similarity ratio.

        A ratio >= LOOP_SIMILARITY_THRESHOLD (default 0.85) signals a loop.
        """
        for _, prev in self._history[-LOOP_LOOKBACK:]:
            ratio = difflib.SequenceMatcher(None, prev, response).ratio()
            if ratio >= LOOP_SIMILARITY_THRESHOLD:
                log.debug("Loop similarity ratio=%.2f detected", ratio)
                return True
        return False

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist(self, user_input: str, ai_response: str) -> None:
        """Save both sides of the turn to the SQLite memory store."""
        if not self._hydrator:
            return
        try:
            await self._hydrator.persist_message(self.session, "user", user_input, self.agent)
            await self._hydrator.persist_message(self.session, "assistant", ai_response, self.agent)
        except Exception as exc:
            log.warning("Memory persist failed (non-fatal): %s", exc)

    async def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return persisted conversation history for this session."""
        if self._store:
            try:
                return await self._store.get_history(self.session, limit=limit)
            except Exception as exc:
                log.warning("Could not fetch history from store: %s", exc)
        # Fall back to in-memory history — interleave user/assistant in turn order
        return [
            {"role": role, "content": msg, "agent": self.agent, "ts": 0}
            for u, a in self._history
            for role, msg in (("user", u), ("assistant", a))
        ]

    async def clear_history(self) -> None:
        """Clear both in-memory and persisted history for this session."""
        self._history.clear()
        self.context_summary = ""
        if self._store:
            try:
                await self._store.clear_history(self.session)
                log.info("History cleared for session=%s", self.session)
            except Exception as exc:
                log.warning("Could not clear store history: %s", exc)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

async def _run_cli() -> None:
    print("Sovereignty AI Studio — Loop-safe conversation (type 'exit' or 'quit' to stop)")
    print(f"Session: default | Sovereign API: {SOVEREIGN_API_URL}")
    print("-" * 60)

    assistant = AIAssistant()
    await assistant.init()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        reply = await assistant.process_user_input(user_input)
        print(f"AI: {reply}\n")


if __name__ == "__main__":
    try:
        asyncio.run(_run_cli())
    except KeyboardInterrupt:
        print("\nStopped.")
