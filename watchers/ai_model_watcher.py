"""
AI Model Selection Watcher

Monitors AI model selection events and routes requests to appropriate models.
Supports Claude, GPT, Grok, Qwen families, and "judge" model routing logic.
"""

import asyncio
import logging
from typing import Optional

log = logging.getLogger("watchers.ai_model")


class AIModelWatcher:
    """
    Watches AI model selection and routing events.
    Integrates with EventBus to monitor model usage and health.
    """

    def __init__(self, bus, model_fixer=None):
        self._bus = bus
        self._model_fixer = model_fixer
        self._task: Optional[asyncio.Task] = None

        # Model usage statistics
        self._model_usage: dict[str, int] = {}
        self._model_errors: dict[str, int] = {}
        self._model_latencies: dict[str, list[float]] = {}

        # Available model families
        self._model_families = {
            "claude": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-sonnet-4-5"],
            "gpt": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "grok": ["grok-1", "grok-2"],
            "qwen": ["qwen-2-72b", "qwen-1.5-14b"],
        }

        # Judge model for routing
        self._judge_model = "claude-sonnet-4-5"

    async def start(self) -> None:
        """Start the AI model watcher."""
        if self._task and not self._task.done():
            return

        # Subscribe to relevant events
        self._bus.subscribe("ai_chat", self._on_ai_chat)
        self._bus.subscribe("ai_response", self._on_ai_response)
        self._bus.subscribe("model_error", self._on_model_error)

        log.info("AIModelWatcher started")

    async def stop(self) -> None:
        """Stop the AI model watcher."""
        # Unsubscribe from events
        self._bus.unsubscribe("ai_chat", self._on_ai_chat)
        self._bus.unsubscribe("ai_response", self._on_ai_response)
        self._bus.unsubscribe("model_error", self._on_model_error)

        log.info("AIModelWatcher stopped")

    async def _on_ai_chat(self, event: dict) -> None:
        """Handle AI chat events."""
        agent = event.get("agent", "unknown")
        model = self._extract_model_from_agent(agent)

        # Track usage
        self._model_usage[model] = self._model_usage.get(model, 0) + 1

        log.debug("AI chat request for model: %s", model)

    async def _on_ai_response(self, event: dict) -> None:
        """Handle AI response events."""
        agent = event.get("agent", "unknown")
        model = self._extract_model_from_agent(agent)

        # Track latency if available
        if "latency_ms" in event:
            if model not in self._model_latencies:
                self._model_latencies[model] = []
            self._model_latencies[model].append(event["latency_ms"])

            # Keep only last 100 latencies
            if len(self._model_latencies[model]) > 100:
                self._model_latencies[model].pop(0)

        log.debug("AI response from model: %s", model)

    async def _on_model_error(self, event: dict) -> None:
        """Handle model error events."""
        model = event.get("model", "unknown")

        # Track errors
        self._model_errors[model] = self._model_errors.get(model, 0) + 1

        log.warning("Model error for: %s (total: %d)", model, self._model_errors[model])

        # Mark model as failed in fixer if available
        if self._model_fixer:
            self._model_fixer.mark_model_failed(model)

    def _extract_model_from_agent(self, agent: str) -> str:
        """Extract model name from agent string."""
        agent_lower = agent.lower()

        # Check for model families
        for family in self._model_families:
            if family in agent_lower:
                return family

        return agent

    def select_model(self, request: dict) -> str:
        """
        Select appropriate model for request.

        Args:
            request: Request dictionary with context

        Returns:
            Selected model name
        """
        # Check if specific model requested
        if "model" in request:
            requested = request["model"]
            if self._is_model_available(requested):
                return requested

        # Use judge model for complex routing
        if request.get("use_judge", False):
            return self._judge_model

        # Default to best available model
        return self._get_best_model()

    def _is_model_available(self, model: str) -> bool:
        """Check if model is available and not failed."""
        if self._model_fixer and self._model_fixer.is_model_failed(model):
            return False

        # Check if model exists in any family
        model_lower = model.lower()
        for family_models in self._model_families.values():
            if any(model_lower in m.lower() or m.lower() in model_lower for m in family_models):
                return True

        return False

    def _get_best_model(self) -> str:
        """Get best available model based on performance metrics."""
        # Prefer models with low error rates and good latency
        best_model = None
        best_score = float("-inf")

        for family, models in self._model_families.items():
            for model in models:
                if self._model_fixer and self._model_fixer.is_model_failed(model):
                    continue

                # Calculate score based on usage, errors, and latency
                usage = self._model_usage.get(model, 0)
                errors = self._model_errors.get(model, 0)
                error_rate = errors / usage if usage > 0 else 0

                avg_latency = 0
                if model in self._model_latencies and self._model_latencies[model]:
                    avg_latency = sum(self._model_latencies[model]) / len(self._model_latencies[model])

                # Score: lower error rate and latency is better
                score = 1.0 - error_rate - (avg_latency / 10000.0)

                if score > best_score:
                    best_score = score
                    best_model = model

        # Default to judge model if no good option found
        return best_model or self._judge_model

    def get_model_stats(self, model: str) -> dict:
        """Get statistics for a specific model."""
        usage = self._model_usage.get(model, 0)
        errors = self._model_errors.get(model, 0)
        latencies = self._model_latencies.get(model, [])

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        error_rate = errors / usage if usage > 0 else 0

        return {
            "usage_count": usage,
            "error_count": errors,
            "error_rate": error_rate,
            "avg_latency_ms": avg_latency,
            "latency_samples": len(latencies),
        }

    def status(self) -> dict:
        """Get current AI model watcher status."""
        return {
            "judge_model": self._judge_model,
            "model_families": self._model_families,
            "model_usage": dict(self._model_usage),
            "model_errors": dict(self._model_errors),
            "total_requests": sum(self._model_usage.values()),
            "total_errors": sum(self._model_errors.values()),
        }
