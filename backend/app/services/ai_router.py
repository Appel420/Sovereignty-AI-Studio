"""
Multi-provider AI router with cascading fallback logic.
Priority order: xAI (Grok) → Anthropic (Claude) → OpenAI (GPT)
Privacy mode forces local-only (no external calls — raises if no provider).
Cost-optimized mode can be configured per-call.

Keep the router privacy-first and vendor-neutral.
"""
import logging
import os
from typing import Optional

from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.xai_provider import XAIProvider

logger = logging.getLogger(__name__)

# Provider preference order (left = highest priority)
PROVIDER_ORDER = ["xai", "anthropic", "openai"]


class AIRouter:
    """
    Routes AI requests across sovereign cloud providers with automatic fallback.

    Fallback chain: xAI → Anthropic → OpenAI
    Privacy mode: raises immediately (no external calls permitted)
    """

    def __init__(self):
        self._providers: dict = {}
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize all configured providers, skip unconfigured ones."""
        candidates = {
            "xai": (XAIProvider, "XAI_API_KEY"),
            "anthropic": (AnthropicProvider, "ANTHROPIC_API_KEY"),
            "openai": (OpenAIProvider, "OPENAI_API_KEY"),
        }
        for name, (cls, env_key) in candidates.items():
            if os.getenv(env_key):
                try:
                    self._providers[name] = cls()
                    logger.info("AI provider initialized: %s", name)
                except Exception as exc:
                    logger.warning("Failed to init provider %s: %s", name, exc)

    @property
    def available_providers(self) -> list:
        return list(self._providers.keys())

    async def chat(
        self,
        prompt: str,
        system: str = "You are a helpful AI assistant.",
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        privacy_mode: bool = False,
    ) -> dict:
        """
        Route a chat request with automatic provider fallback.

        Args:
            prompt: The user's message.
            system: System prompt / instructions.
            preferred_provider: Try this provider first if available.
            model: Specific model name (provider-specific). Uses provider default if None.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature.
            privacy_mode: If True, raises immediately (for future sovereign inference node).

        Returns:
            Normalized response dict with keys: provider, model, text, tokens, latency_ms.

        Raises:
            RuntimeError: All providers failed or privacy_mode with no local provider.
        """
        if privacy_mode:
            raise RuntimeError(
                "Privacy mode enabled: external AI calls are not permitted. "
                "Configure a sovereign local inference node."
            )

        order = self._build_order(preferred_provider)
        errors: list = []

        for provider_name in order:
            provider = self._providers.get(provider_name)
            if not provider:
                continue
            kwargs: dict = {
                "prompt": prompt,
                "system": system,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if model:
                kwargs["model"] = model
            try:
                result = await provider.chat(**kwargs)
                if len(errors) > 0:
                    result["fallback_from"] = errors
                return result
            except Exception as exc:
                logger.warning(
                    "Provider %s failed: %s — trying next", provider_name, exc
                )
                errors.append({"provider": provider_name, "error": str(exc)})

        raise RuntimeError(
            f"All AI providers failed. Errors: {errors}. "
            f"Available providers: {self.available_providers}"
        )

    def _build_order(self, preferred: Optional[str]) -> list:
        """Build provider priority list, putting preferred first."""
        order = PROVIDER_ORDER.copy()
        if preferred and preferred in self._providers:
            order = [preferred] + [p for p in order if p != preferred]
        return order

    async def health_check(self) -> dict:
        """Return health status of all configured providers."""
        status = {}
        for name, provider in self._providers.items():
            try:
                status[name] = {"healthy": await provider.health_check()}
            except Exception as exc:
                status[name] = {"healthy": False, "error": str(exc)}
        return {
            "router": "sovereign",
            "providers": status,
            "available": list(status.keys()),
        }


# Module-level singleton
ai_router = AIRouter()
