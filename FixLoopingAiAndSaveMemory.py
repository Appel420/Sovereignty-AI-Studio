#!/usr/bin/env python3
"""Loop-safe sovereign AI assistant with explicit session authorization.

A conversation session is application state, not an authority credential.
Callers must provide a locally issued, signed session proof containing the
identity and the ``ai.inference`` capability before this assistant can route an
AI request or persist session memory.
"""
from __future__ import annotations

import asyncio
import difflib
import json
import logging
import os
import sys
import urllib.request
from typing import Any

from backend.coordination.session_authorization import (
    SessionAuthorization,
    SessionAuthorizationError,
    verify_session_proof,
)

log = logging.getLogger("fix_loop_memory")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

SOVEREIGN_API_URL = os.environ.get(
    "SOVEREIGN_API_URL", "http://localhost:9899/api/ai"
).rstrip("/")
LOOP_SIMILARITY_THRESHOLD = float(os.environ.get("LOOP_SIMILARITY_THRESHOLD", "0.85"))
LOOP_LOOKBACK = int(os.environ.get("LOOP_LOOKBACK", "4"))
SUMMARY_LOOKBACK = int(os.environ.get("SUMMARY_LOOKBACK", "6"))
MAX_IN_MEMORY_TURNS = int(os.environ.get("MAX_IN_MEMORY_TURNS", "100"))
REFRAME_PREVIEW_LENGTH = 300
AI_INFERENCE_CAPABILITY = "ai.inference"


def _try_import_memory():
    try:
        from memory.store import MemoryStore
        from memory.hydration import MemoryHydrator
        return MemoryStore, MemoryHydrator
    except ImportError as exc:
        log.warning("memory module not available (persistence disabled): %s", exc)
        return None, None


def _chat_sovereign_sync(
    messages: list[dict],
    agent: str,
    authorization: SessionAuthorization,
) -> str:
    """Route only after an already-verified session capability is present."""
    if not authorization.allows(AI_INFERENCE_CAPABILITY):
        raise SessionAuthorizationError("session lacks ai.inference capability")

    try:
        from ai_core.sovereign_bridge import SovereignBridge

        bridge = SovereignBridge()
        return bridge.chat(messages)
    except Exception as exc:  # noqa: BLE001
        log.warning("SovereignBridge failed, using authorized HTTP fallback: %s", exc)

    body = json.dumps(
        {
            "messages": messages,
            "max_tokens": 2048,
            "context": {
                "agent": agent,
                "session_id": authorization.session_id,
                "identity_id": authorization.identity_id,
                "mode": authorization.mode,
            },
        }
    ).encode()
    req = urllib.request.Request(
        f"{SOVEREIGN_API_URL}/chat",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Sovereign-Session": authorization.session_id,
            "X-Sovereign-Identity": authorization.identity_id,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
            return (
                data.get("text")
                or data.get("response")
                or data.get("choices", [{}])[0].get("message", {}).get("content", "")
                or "[no response]"
            )
    except Exception as exc:  # noqa: BLE001
        log.error("Authorized sovereign HTTP API error: %s", exc)
        return f"[Sovereign bridge error: {exc}]"


async def _chat_sovereign(
    messages: list[dict],
    agent: str,
    authorization: SessionAuthorization,
) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _chat_sovereign_sync,
        messages,
        agent,
        authorization,
    )


class AIAssistant:
    """Sovereign AI assistant with loop detection and authorized memory."""

    def __init__(
        self,
        session_proof: str,
        *,
        session: str | None = None,
        agent: str = "sovereign",
    ) -> None:
        self.authorization = self._verify_session(session_proof)
        if session is not None and session != self.authorization.session_id:
            raise SessionAuthorizationError("session argument does not match signed session")
        if not self.authorization.allows(AI_INFERENCE_CAPABILITY):
            raise SessionAuthorizationError("session lacks ai.inference capability")

        self.session = self.authorization.session_id
        self.agent = agent
        self._history: list[tuple[str, str]] = []
        self.context_summary = ""

        store_cls, hydrator_cls = _try_import_memory()
        self._store = store_cls() if store_cls else None
        self._hydrator = (
            hydrator_cls(self._store) if (hydrator_cls and self._store) else None
        )

    @staticmethod
    def _verify_session(proof: str) -> SessionAuthorization:
        try:
            return verify_session_proof(proof)
        except SessionAuthorizationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SessionAuthorizationError("session authorization failed") from exc

    async def init(self) -> None:
        if self._store:
            try:
                await self._store.init()
                log.info("MemoryStore initialised for authorized session=%s", self.session)
            except Exception as exc:
                log.warning("MemoryStore init failed: %s", exc)

    async def process_user_input(self, user_input: str) -> str:
        if not self.authorization.allows(AI_INFERENCE_CAPABILITY):
            raise SessionAuthorizationError("session is not authorized for AI inference")

        self._update_context_summary(user_input)
        messages = self._build_messages(user_input)
        ai_response = await _chat_sovereign(messages, self.agent, self.authorization)

        if self._detect_loop(ai_response):
            log.info("Loop detected; reframing prompt for session=%s", self.session)
            reframed_messages = self._build_messages(
                user_input, reframe=True, previous_response=ai_response
            )
            ai_response = await _chat_sovereign(
                reframed_messages, self.agent, self.authorization
            )

        self._history.append((user_input, ai_response))
        if len(self._history) > MAX_IN_MEMORY_TURNS:
            self._history = self._history[-MAX_IN_MEMORY_TURNS:]

        await self._persist(user_input, ai_response)
        return ai_response

    def _update_context_summary(self, incoming_user_input: str) -> None:
        del incoming_user_input
        recent = self._history[-SUMMARY_LOOKBACK:]
        lines = [f"User: {user}\nAI: {answer}" for user, answer in recent]
        self.context_summary = (
            "Recent conversation:\n" + "\n---\n".join(lines)
            if lines
            else "(No prior conversation in this session.)"
        )

    def _build_messages(
        self,
        user_input: str,
        *,
        reframe: bool = False,
        previous_response: str = "",
    ) -> list[dict[str, str]]:
        system_parts = [
            "You are a sovereign AI assistant running entirely on self-hosted infrastructure. "
            "No data leaves the network. Be precise, production-ready, and never fabricate data.",
            "",
            self.context_summary,
            "",
            f"Authorized identity: {self.authorization.identity_id}",
            f"Authorized runtime mode: {self.authorization.mode}",
        ]
        if reframe:
            system_parts += [
                "",
                "IMPORTANT: Your previous response may have been repetitive. "
                "Approach this from a completely different angle. "
                f"Previous attempt: {previous_response[:REFRAME_PREVIEW_LENGTH]}",
            ]
        return [
            {"role": "system", "content": "\n".join(system_parts).strip()},
            {"role": "user", "content": user_input},
        ]

    def _detect_loop(self, response: str) -> bool:
        for _, previous in self._history[-LOOP_LOOKBACK:]:
            ratio = difflib.SequenceMatcher(None, previous, response).ratio()
            if ratio >= LOOP_SIMILARITY_THRESHOLD:
                log.debug("Loop similarity ratio=%.2f detected", ratio)
                return True
        return False

    async def _persist(self, user_input: str, ai_response: str) -> None:
        if not self._hydrator:
            return
        try:
            await self._hydrator.persist_message(
                self.session, "user", user_input, self.agent
            )
            await self._hydrator.persist_message(
                self.session, "assistant", ai_response, self.agent
            )
        except Exception as exc:
            log.warning("Memory persist failed (non-fatal): %s", exc)

    async def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        if self._store:
            try:
                return await self._store.get_history(self.session, limit=limit)
            except Exception as exc:
                log.warning("Could not fetch history from store: %s", exc)
        return [
            {"role": role, "content": message, "agent": self.agent, "ts": 0}
            for user, assistant in self._history
            for role, message in (("user", user), ("assistant", assistant))
        ]

    async def clear_history(self) -> None:
        self._history.clear()
        self.context_summary = ""
        if self._store:
            try:
                await self._store.clear_history(self.session)
                log.info("History cleared for authorized session=%s", self.session)
            except Exception as exc:
                log.warning("Could not clear store history: %s", exc)


async def _run_cli() -> None:
    print("Sovereignty AI Studio — authorized loop-safe conversation")
    proof = os.environ.get("SOVEREIGN_SESSION_PROOF", "")
    if not proof:
        raise SystemExit("DENY: SOVEREIGN_SESSION_PROOF is required")

    assistant = AIAssistant(proof)
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
