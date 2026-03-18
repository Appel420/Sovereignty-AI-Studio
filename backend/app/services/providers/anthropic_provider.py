"""
Anthropic provider adapter — routes requests through the Anthropic Messages API.
Uses httpx for async HTTP, no vendor SDK dependency.
"""
import time
import os
import httpx
from typing import Optional

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-opus-4-5"
REQUEST_TIMEOUT = 60.0


class AnthropicProvider:
    """Wraps Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

    async def chat(
        self,
        prompt: str,
        system: str = "You are a helpful AI assistant.",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> dict:
        """Send a messages request. Returns normalized response dict."""
        start = time.monotonic()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{ANTHROPIC_API_BASE}/messages",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        latency_ms = (time.monotonic() - start) * 1000
        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        return {
            "provider": self.name,
            "model": model,
            "text": text,
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "latency_ms": round(latency_ms, 2),
        }

    async def health_check(self) -> bool:
        return bool(self.api_key)
