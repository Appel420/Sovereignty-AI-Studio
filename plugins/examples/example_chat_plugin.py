"""
Example chat plugin — demonstrates the Sovereignty AI Studio Plugin SDK.

This plugin routes chat messages through the sovereign AI router
(xAI → Anthropic → OpenAI, no Ollama/Meta) and returns the response.

Entry point: plugins.examples.example_chat_plugin:ExampleChatPlugin
"""
import asyncio
from typing import Any, Dict, Optional

from plugins.sdk.plugin_base import PluginBase


class ExampleChatPlugin(PluginBase):
    """
    A simple chat plugin that wraps the sovereign AI router.

    Install via marketplace:
        POST /api/v1/marketplace/install
        {
            "name": "example_chat",
            "display_name": "Example Chat Plugin",
            "version": "1.0.0",
            "entry_point": "plugins.examples.example_chat_plugin:ExampleChatPlugin",
            "category": "ai",
            "default_config": {
                "preferred_provider": "xai",
                "system_prompt": "You are a helpful assistant.",
                "max_tokens": 512
            }
        }
    """

    name = "example_chat"
    display_name = "Example Chat Plugin"
    version = "1.0.0"
    description = "Routes chat messages through the sovereign AI router with provider fallback."
    author = "Sovereignty One"
    category = "ai"

    def configure(self, config: Dict) -> None:
        self.preferred_provider: Optional[str] = self.get_config(
            "preferred_provider", "xai"
        )
        self.system_prompt: str = self.get_config(
            "system_prompt", "You are a helpful assistant."
        )
        self.max_tokens: int = int(self.get_config("max_tokens", 512))
        self.logger.info(
            "ExampleChatPlugin configured: provider=%s max_tokens=%d",
            self.preferred_provider,
            self.max_tokens,
        )

    def run(self, payload: Dict) -> Any:
        """
        Process a chat message.

        Expected payload:
            {"prompt": "What is sovereignty?", "system": "Optional override"}

        Returns:
            {"text": "...", "provider": "xai", "tokens": 42}
        """
        prompt = payload.get("prompt", "")
        if not prompt:
            return {"error": "No prompt provided", "text": ""}

        system = payload.get("system", self.system_prompt)

        try:
            result = self._run_async_chat(prompt, system)
            return {
                "text": result.get("text", ""),
                "provider": result.get("provider", "unknown"),
                "model": result.get("model", "unknown"),
                "tokens": result.get("total_tokens", 0),
                "latency_ms": result.get("latency_ms", 0),
            }
        except Exception as exc:
            self.logger.error("ExampleChatPlugin run failed: %s", exc)
            return {"error": str(exc), "text": ""}

    def _run_async_chat(self, prompt: str, system: str) -> dict:
        """Bridge sync plugin interface to async AI router."""
        from app.services.ai_router import ai_router

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # We're inside an async context — create a task-compatible future
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    ai_router.chat(
                        prompt=prompt,
                        system=system,
                        preferred_provider=self.preferred_provider,
                        max_tokens=self.max_tokens,
                    ),
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                ai_router.chat(
                    prompt=prompt,
                    system=system,
                    preferred_provider=self.preferred_provider,
                    max_tokens=self.max_tokens,
                )
            )

    def health_check(self) -> bool:
        """Healthy if the AI router has at least one provider configured."""
        try:
            from app.services.ai_router import ai_router
            return len(ai_router.available_providers) > 0
        except Exception:
            return False

    def start(self) -> None:
        super().start()
        self.logger.info(
            "ExampleChatPlugin ready — preferred provider: %s",
            self.preferred_provider,
        )

    def stop(self) -> None:
        super().stop()
