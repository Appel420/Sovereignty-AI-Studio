"""
OpenAI provider adapter — routes requests through the OpenAI API.
Uses httpx for async HTTP, no vendor SDK dependency.
"""
import time
import os
import httpx
from typing import Optional

OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o"
REQUEST_TIMEOUT = 60.0


class OpenAIProvider:
    """Wraps OpenAI Chat Completions API."""

    name = "openai"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

    async def chat(
        self,
        prompt: str,
        system: str = "You are a helpful AI assistant.",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> dict:
        """Send a chat completion request. Returns normalized response dict."""
        start = time.monotonic()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        latency_ms = (time.monotonic() - start) * 1000
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "provider": self.name,
            "model": model,
            "text": choice,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": round(latency_ms, 2),
        }

    async def health_check(self) -> bool:
        """Lightweight check — verifies the API key is configured."""
        return bool(self.api_key)
