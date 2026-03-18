"""
xAI / Grok provider adapter — routes requests through the xAI API.
The xAI API is OpenAI-compatible; we target the /v1/chat/completions endpoint.
"""
import time
import os
import httpx
from typing import Optional

XAI_API_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-3"
REQUEST_TIMEOUT = 60.0


class XAIProvider:
    """Wraps xAI (Grok) Chat Completions API."""

    name = "xai"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("XAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("XAI_API_KEY is not configured")

    async def chat(
        self,
        prompt: str,
        system: str = "You are a helpful AI assistant.",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> dict:
        """Send a chat completion request via xAI-compatible API."""
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
                f"{XAI_API_BASE}/chat/completions",
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
        return bool(self.api_key)
