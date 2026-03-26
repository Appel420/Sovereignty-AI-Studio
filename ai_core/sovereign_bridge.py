"""
Sovereignty AI Studio — Sovereign Bridge (Python side)
Routes all AI requests through self-hosted providers only.
No external SaaS. No data leaves the infrastructure.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider registry (ordered; never falls back to external SaaS)
# ---------------------------------------------------------------------------
_DEFAULT_ORDER = os.getenv(
    "SOVEREIGN_PROVIDER_ORDER", "local_gguf,local_onnx,sovereign_api"
).split(",")


class ProviderError(RuntimeError):
    """Raised when all providers fail."""


class SovereignBridge:
    """
    Abstract provider interface that routes AI requests to self-hosted models.

    Instantiate once per application and reuse across requests:

        bridge = SovereignBridge()
        response = bridge.chat([{"role": "user", "content": "Hello"}],
                               context={"userId": "u1", "orgId": "o1"})
    """

    def __init__(
        self,
        provider_order: Optional[List[str]] = None,
        *,
        sovereign_model_path: Optional[str] = None,
        sovereign_onnx_path: Optional[str] = None,
        sovereign_api_url: Optional[str] = None,
    ):
        self._order = provider_order or _DEFAULT_ORDER
        self._cfg = {
            "model_path": sovereign_model_path or os.getenv("SOVEREIGN_MODEL_PATH"),
            "onnx_path": sovereign_onnx_path or os.getenv("SOVEREIGN_ONNX_PATH"),
            "api_url": sovereign_api_url or os.getenv(
                "SOVEREIGN_API_URL", "http://localhost:9898/api/ai"
            ),
        }
        self._providers: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        context: Optional[Dict[str, str]] = None,
        max_tokens: int = 1200,
        stream: bool = False,
    ) -> str | Generator[str, None, None]:
        """
        Route a chat request through sovereign providers.

        :param messages:   OpenAI-style message list
                           [{"role": "user", "content": "..."}]
        :param context:    Injection dict with userId, orgId, projectId
        :param max_tokens: Response token limit
        :param stream:     If True, return a string generator
        :returns:          Full response string or generator of chunks
        """
        context = context or {}
        last_error: Optional[Exception] = None

        for provider_name in self._order:
            provider_name = provider_name.strip()
            try:
                provider = self._get_provider(provider_name)
                logger.info(
                    "Trying provider=%s userId=%s orgId=%s",
                    provider_name,
                    context.get("userId"),
                    context.get("orgId"),
                )
                result = provider.chat(
                    messages,
                    context=context,
                    max_tokens=max_tokens,
                    stream=stream,
                )
                return result
            except Exception as exc:  # noqa: BLE001
                logger.warning("Provider %s failed: %s", provider_name, exc)
                last_error = exc

        raise ProviderError(
            f"All sovereign providers exhausted. Last error: {last_error}"
        )

    def health(self) -> Dict[str, Any]:
        """Return health status for all configured providers."""
        status: Dict[str, Any] = {}
        for name in self._order:
            name = name.strip()
            try:
                provider = self._get_provider(name)
                status[name] = provider.health()
            except Exception as exc:  # noqa: BLE001
                status[name] = {"ok": False, "error": str(exc)}
        return status

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_provider(self, name: str) -> Any:
        """Lazy-load and cache provider instances."""
        if name not in self._providers:
            self._providers[name] = self._load_provider(name)
        return self._providers[name]

    def _load_provider(self, name: str) -> Any:
        if name == "local_gguf":
            from ai_core.providers.local_inference import GGUFProvider

            return GGUFProvider(self._cfg["model_path"])
        if name == "local_onnx":
            from ai_core.providers.local_inference import ONNXProvider

            return ONNXProvider(self._cfg["onnx_path"])
        if name == "sovereign_api":
            from ai_core.providers.sovereign_api import SovereignAPIProvider

            return SovereignAPIProvider(self._cfg["api_url"])
        raise ValueError(f"Unknown sovereign provider: {name!r}")


# ---------------------------------------------------------------------------
# Usage tracking helper (thin wrapper — analytics module does the heavy lift)
# ---------------------------------------------------------------------------

def track_usage(
    user_id: str,
    org_id: str,
    tokens: int,
    provider: str,
    project_id: Optional[str] = None,
) -> None:
    """Record token usage — delegates to analytics.usage_tracker."""
    try:
        from analytics.usage_tracker import record_usage

        record_usage(
            user_id=user_id,
            org_id=org_id,
            tokens=tokens,
            provider=provider,
            project_id=project_id,
            ts=time.time(),
        )
    except ImportError:
        logger.debug("analytics.usage_tracker not available; skipping usage record")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Usage tracking failed: %s", exc)
