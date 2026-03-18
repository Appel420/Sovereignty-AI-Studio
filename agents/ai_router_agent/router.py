"""AI Router Agent — routes tasks to the appropriate AI provider.

Supported providers (in order of priority):
1. OpenAI (GPT)
2. Anthropic (Claude)
3. xAI (Grok)

The router requests Judge approval before executing any task and releases
the resource lock afterwards, whether the task succeeds or fails.

Environment variables
---------------------
OPENAI_API_KEY    — OpenAI API key
ANTHROPIC_API_KEY — Anthropic API key
XAI_API_KEY       — xAI / Grok API key
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Provider constants
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_XAI = "xai"

# Task-type → preferred provider mapping
_TASK_PROVIDER_MAP: Dict[str, str] = {
    "code": PROVIDER_OPENAI,
    "analysis": PROVIDER_ANTHROPIC,
    "search": PROVIDER_XAI,
    "creative": PROVIDER_ANTHROPIC,
    "reasoning": PROVIDER_XAI,
}

_DEFAULT_PROVIDER_ORDER = [PROVIDER_OPENAI, PROVIDER_ANTHROPIC, PROVIDER_XAI]


def _key_available(provider: str) -> bool:
    env_map = {
        PROVIDER_OPENAI: "OPENAI_API_KEY",
        PROVIDER_ANTHROPIC: "ANTHROPIC_API_KEY",
        PROVIDER_XAI: "XAI_API_KEY",
    }
    key = os.getenv(env_map.get(provider, ""), "")
    return bool(key)


def _select_provider(task_type: str) -> Optional[str]:
    """Return the first available provider for *task_type*."""
    preferred = _TASK_PROVIDER_MAP.get(task_type)
    candidates = (
        [preferred] + [p for p in _DEFAULT_PROVIDER_ORDER if p != preferred]
        if preferred
        else _DEFAULT_PROVIDER_ORDER
    )
    for provider in candidates:
        if _key_available(provider):
            return provider
    return None


async def _call_openai(prompt: str, system: str) -> str:
    """Call OpenAI Chat Completions API."""
    import httpx  # type: ignore

    api_key = os.environ["OPENAI_API_KEY"]
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]


async def _call_anthropic(prompt: str, system: str) -> str:
    """Call Anthropic Messages API."""
    import httpx  # type: ignore

    api_key = os.environ["ANTHROPIC_API_KEY"]
    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    return data["content"][0]["text"]


async def _call_xai(prompt: str, system: str) -> str:
    """Call xAI (Grok) Chat Completions API."""
    import httpx  # type: ignore

    api_key = os.environ["XAI_API_KEY"]
    payload = {
        "model": "grok-3",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]


_PROVIDER_CALLERS = {
    PROVIDER_OPENAI: _call_openai,
    PROVIDER_ANTHROPIC: _call_anthropic,
    PROVIDER_XAI: _call_xai,
}


class AIRouterAgent:
    """Routes AI inference tasks to the best available provider."""

    AGENT_ID = "ai_router"

    def __init__(self, judge: Any) -> None:
        self._judge = judge

    async def route(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """Route *task* to an appropriate AI provider under Judge supervision.

        The *task* dict should contain:
        - ``prompt`` (str) — the user prompt
        - ``system`` (str, optional) — the system message
        - ``task_type`` (str, optional) — hint for provider selection

        Returns:
            ``(success: bool, result_or_error: str)``
        """
        task_type = task.get("task_type", "")
        provider = _select_provider(task_type)
        if provider is None:
            err = "No AI provider credentials available"
            logger.error(err)
            return False, err

        judge_task = {**task, "resource": provider}
        approved, reason = await self._judge.approve_task(self.AGENT_ID, judge_task)
        if not approved:
            return False, f"Judge rejected task: {reason}"

        prompt = task.get("prompt", "")
        system = task.get("system", "You are a helpful sovereign AI assistant.")
        caller = _PROVIDER_CALLERS[provider]
        try:
            result = await caller(prompt, system)
            logger.info("AI Router: %s responded successfully", provider)
            return True, result
        except Exception as exc:
            logger.error("AI Router: %s failed: %s", provider, exc, exc_info=True)
            return False, f"Provider '{provider}' error: {exc}"
        finally:
            await self._judge.release_task(self.AGENT_ID, provider)
