#!/usr/bin/env python3
"""Loop-safe sovereign AI assistant with explicit session authorization.

The assistant is deliberately fail-closed: a session must carry the locally
issued ``ai.inference`` capability, the HTTP fallback must remain loopback-only,
and infrastructure failures are exceptions rather than assistant messages.
Conversation persistence is also treated as a runtime invariant when the
memory subsystem is present.
"""
from __future__ import annotations

import asyncio
import difflib
import ipaddress
import json
import logging
import os
import sys
import urllib.parse
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
_ALLOWED_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _validate_configuration() -> None:
    """Reject malformed or non-loopback fallback endpoints before startup."""
    if not 0 < LOOP_SIMILARITY_THRESHOLD <= 1:
        raise ValueError("LOOP_SIMILARITY_THRESHOLD must be in (0, 1]")
    if LOOP_LOOKBACK < 1 or SUMMARY_LOOKBACK < 1 or MAX_IN_MEMORY_TURNS < 1:
        raise ValueError("loop, summary, and memory limits must be positive")

    parsed = urllib.parse.urlparse(SOVEREIGN_API_URL)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("SOVEREIGN_API_URL must be an HTTP(S) URL")
    host = parsed.hostname.lower().rstrip(".")
    if host not in _ALLOWED_LOOPBACK_HOSTS:
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise ValueError("SOVEREIGN_API_URL must resolve to loopback")
        except ValueError as exc:
            raise ValueError("SOVEREIGN_API_URL must use a loopback host") from exc


_validate_configuration()


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
        return SovereignBridge().chat(messages)
    except Exception as exc:  # noqa: BLE001
        log.warning("SovereignBridge failed; using loopback HTTP fallback: %s", exc)

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
    ).encode("utf-8")
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
    except Exception as exc:  # noqa: BLE001
        log.error("Sovereign HTTP API failed: %s", exc)
        raise RuntimeError("sovereign AI execution failed") from exc

    text = (
        data.get("text")
        or data.get("response")
        or data.get("choices", [{}])[0].get("message", {}).get("content", "")
    )
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("sovereign AI returned no response")
    return text


async def _chat_sovereign(
    messages: list[dict],
    agent: str,
    authorization: SessionAuthorization,
) -> str:
    return await asyncio.get_running_loop().run_in_executor(
        None, _chat_sovereign_sync, messages, agent, authorization
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
        self._memory_ready = False

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
        """Initialize mandatory persistence before accepting conversation turns."""
        if not self._store or not self._hydrator:
            raise RuntimeError("MemoryStore/Mem​oryHydrator unavailable; startup denied")
        try:
            await self._store.init()
        except Exception as exc:  # noqa: BLE001
            log.error("MemoryStore initialization failed")
            raise RuntimeError("memory subsystem initialization failed") from exc
        self._memory_ready = True
        log.info("MemoryStore initialized for authorized session=%s", self.session)

    async def process_user_input(self, user_input: str) -> str:
        if not self.authorization.allows(AI_INFERENCE_CAPABILITY):
            raise SessionAuthorizationError("session is not authorized for AI inference")
        if not self._memory_ready:
            raise RuntimeError("assistant is not initialized")
        if not isinstance(user_input, str) or not user_input.strip():
            raise ValueError("user_input must be a non-empty string")

        self._update_context_summary()
        ai_response = await _chat_sovereign(
            self._build_messages(user_input), self.agent, self.authorization
        )

        if self._detect_loop(ai_response):
            log.info("Loop detected; reframing prompt for session=%s", self.session)
            ai_response = await _chat_sovereign(
                self._build_messages(
                    user_input, reframe=True, previous_response=ai_response
                ),
                self.agent,
                self.authorization,
            )
            if self._detect_loop(ai_response):
                raise RuntimeError("sovereign AI remained repetitive after one reframe")

        await self._persist(user_input, ai_response)
        self._history.append((user_input, ai_response))
        if len(self._history) > MAX_IN_MEMORY_TURNS:
            del self._history[:-MAX_IN_MEMORY_TURNS]
        return ai_response

    def _update_context_summary(self) -> None:
        recent = self._history[-SUMMARY_LOOKBACK:]
        self.context_summary = (
            "Recent conversation:\n" + "\n---\n".join(
                f"User: {user}\nAI: {answer}" for user, answer in recent
            )
            if recent
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
            self.context_summary,
            f"Authorized identity: {self.authorization.identity_id}",
            f"Authorized runtime mode: {self.authorization.mode}",
        ]
        if reframe:
            system_parts.extend(
                [
                    "IMPORTANT: Your previous response was repetitive. Approach this from a "
                    "completely different angle.",
                    f"Previous attempt: {previous_response[:REFRAME_PREVIEW_LENGTH]}",
                ]
            )
        return [
            {"role": "system", "content": "\n\n".join(system_parts).strip()},
            {"role": "user", "content": user_input},
        ]

    def _detect_loop(self, response: str) -> bool:
        return any(
            difflib.SequenceMatcher(None, previous, response).ratio()
            >= LOOP_SIMILARITY_THRESHOLD
            for _, previous in self._history[-LOOP_LOOKBACK:]
        )

    async def _persist(self, user_input: str, ai_response: str) -> None:
        if not self._hydrator:
            raise RuntimeError("memory persistence is unavailable")
        try:
            await self._hydrator.persist_message(
                self.session, "user", user_input, self.agent
            )
            await self._hydrator.persist_message(
                self.session, "assistant", ai_response, self.agent
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Memory persistence failed")
            raise RuntimeError("conversation persistence failed") from exc

    async def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if self._store:
            try:
                return await self._store.get_history(self.session, limit=limit)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("could not fetch conversation history") from exc
        return []

    async def clear_history(self) -> None:
        self._history.clear()
        self.context_summary = ""
        if not self._store:
            raise RuntimeError("memory persistence is unavailable")
        try:
            await self._store.clear_history(self.session)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("could not clear conversation history") from exc


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
