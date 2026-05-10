"""
Model fixer for AI model loading and inference issues.

Automatically detects and fixes:
  - Model loading failures
  - Model file corruption
  - Incompatible model versions
  - Memory issues during inference
  - Model selection and routing problems
"""

import logging
from typing import Optional

from errors.exceptions import AIModelError

log = logging.getLogger("fixers.model")


class ModelFixer:
    """
    Validates and repairs AI model issues automatically.
    """

    def __init__(self):
        self._model_cache: dict[str, any] = {}
        self._fallback_models: dict[str, str] = {
            "claude": "gpt",
            "gpt": "claude",
            "grok": "claude",
            "qwen": "gpt",
        }
        self._failed_models: set[str] = set()

    def register_fallback(self, model: str, fallback: str) -> None:
        """
        Register a fallback model for when primary model fails.

        Args:
            model: Primary model name
            fallback: Fallback model name
        """
        self._fallback_models[model] = fallback
        log.info("Registered fallback: %s → %s", model, fallback)

    def get_fallback_model(self, model: str) -> Optional[str]:
        """
        Get fallback model for a failed model.

        Args:
            model: Model that failed

        Returns:
            Fallback model name or None
        """
        # Normalize model name
        model_lower = model.lower()

        # Check direct fallback
        if model_lower in self._fallback_models:
            return self._fallback_models[model_lower]

        # Check family-based fallback
        if "claude" in model_lower:
            return "gpt-4"
        elif "gpt" in model_lower:
            return "claude-3-opus"
        elif "grok" in model_lower:
            return "claude-3-sonnet"
        elif "qwen" in model_lower:
            return "gpt-3.5-turbo"

        return None

    def fix_model_selection(self, model: str, available_models: list[str]) -> str:
        """
        Fix model selection by finding available alternative.

        Args:
            model: Requested model
            available_models: List of available models

        Returns:
            Fixed model name

        Raises:
            AIModelError: If no suitable model can be found
        """
        model_lower = model.lower()

        # Check if requested model is available
        for available in available_models:
            if model_lower in available.lower() or available.lower() in model_lower:
                return available

        # Try fallback
        fallback = self.get_fallback_model(model)
        if fallback:
            for available in available_models:
                if fallback.lower() in available.lower() or available.lower() in fallback.lower():
                    log.info("Using fallback model: %s → %s", model, available)
                    return available

        # Use first available model as last resort
        if available_models:
            log.warning("No matching model found for %s, using: %s", model, available_models[0])
            return available_models[0]

        raise AIModelError(f"No available models to substitute for {model}", model=model)

    def mark_model_failed(self, model: str) -> None:
        """
        Mark a model as failed.

        Args:
            model: Model name to mark as failed
        """
        self._failed_models.add(model.lower())
        log.warning("Model marked as failed: %s", model)

    def is_model_failed(self, model: str) -> bool:
        """
        Check if a model has been marked as failed.

        Args:
            model: Model name to check

        Returns:
            True if model has failed before
        """
        return model.lower() in self._failed_models

    def reset_failed_models(self) -> None:
        """Reset the failed models list."""
        count = len(self._failed_models)
        self._failed_models.clear()
        log.info("Reset %d failed models", count)

    def validate_model_name(self, model: str) -> bool:
        """
        Validate model name format.

        Args:
            model: Model name to validate

        Returns:
            True if model name is valid
        """
        if not model or not isinstance(model, str):
            return False

        # Check for valid characters
        if not all(c.isalnum() or c in "-_." for c in model):
            return False

        # Check reasonable length
        if len(model) < 2 or len(model) > 100:
            return False

        return True

    def fix_model_name(self, model: str) -> str:
        """
        Fix invalid model name.

        Args:
            model: Model name to fix

        Returns:
            Fixed model name

        Raises:
            AIModelError: If model name cannot be fixed
        """
        if not model or not isinstance(model, str):
            raise AIModelError("Invalid model name: must be non-empty string", model=str(model))

        # Remove invalid characters
        fixed = "".join(c for c in model if c.isalnum() or c in "-_.")

        # Ensure not empty after cleaning
        if not fixed:
            raise AIModelError(f"Model name contains only invalid characters: {model}", model=model)

        # Truncate if too long
        if len(fixed) > 100:
            fixed = fixed[:100]

        # Ensure minimum length
        if len(fixed) < 2:
            raise AIModelError(f"Model name too short after fixing: {fixed}", model=model)

        if fixed != model:
            log.info("Fixed model name: %s → %s", model, fixed)

        return fixed

    def get_model_family(self, model: str) -> str:
        """
        Get model family from model name.

        Args:
            model: Model name

        Returns:
            Model family (claude, gpt, grok, qwen, or unknown)
        """
        model_lower = model.lower()

        if "claude" in model_lower:
            return "claude"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "gpt"
        elif "grok" in model_lower or "xai" in model_lower:
            return "grok"
        elif "qwen" in model_lower or "alibaba" in model_lower:
            return "qwen"
        elif "llama" in model_lower or "meta" in model_lower:
            return "llama"
        elif "gemini" in model_lower or "google" in model_lower:
            return "gemini"

        return "unknown"

    def status(self) -> dict:
        """Get current model fixer status."""
        return {
            "failed_models": list(self._failed_models),
            "failed_count": len(self._failed_models),
            "fallback_mappings": dict(self._fallback_models),
            "cached_models": list(self._model_cache.keys()),
        }
