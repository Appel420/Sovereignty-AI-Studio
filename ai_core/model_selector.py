"""
Sovereignty AI Studio — AI Model Selector.

Provides a :class:`ModelCategory` enum, a ``CATEGORY_MODELS`` registry,
and a :func:`build_judge` factory that instantiates the appropriate
AI model wrapper for a given model name.

Judge routing:
    The ``JUDGE`` category contains a single entry that acts as the
    meta-level referee routing all selection logic.  It is never
    treated as a peer model.

Usage::

    from ai_core.model_selector import build_judge, get_models_summary

    instance = build_judge(model="gpt-4o")
    summary  = get_models_summary()
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model category enum
# ---------------------------------------------------------------------------


class ModelCategory(Enum):
    """Categorises available LLM/VLM models by provider and use-case."""

    JUDGE = "Judge Models"          # Meta-level referee — routes all selection logic
    CORE_GROK = "Core Grok"
    MEDICAL = "Medical"
    SECURITY = "Security / Compliance"
    REGIONAL = "Regional / Legal"
    EXPERIMENTAL = "Experimental"
    GPT4 = "GPT-4 Series"
    GPT35 = "GPT-3.5 Series"
    GPT54 = "GPT-5.4 Codex"
    CLAUDE = "Claude Models"
    QWEN = "Qwen Models"


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

# Each entry is (display_name, model_version_id).
# MEDICAL: HIPAA-compliant models are listed first for compliance visibility.

CATEGORY_MODELS: Dict[ModelCategory, List[Tuple[str, str]]] = {
    ModelCategory.JUDGE: [
        # This instance routes all selection logic — it's THE judge, not a peer.
        ("judge-model-super-grok-heavy-4-20", "judge-grok-4-20"),
    ],
    ModelCategory.CORE_GROK: [
        ("Grok-1.5-314B", "Grok-1.5-314B"),
        ("Grok-1.5-Code", "Grok-1.5-Code"),
        ("Grok-1.5-Flash", "Grok-1.5-Flash"),
        ("Grok-1.5-Pro", "Grok-1.5-Pro"),
        ("Grok-1.5-Preview", "Grok-1.5-Preview"),
    ],
    ModelCategory.MEDICAL: [
        # --- HIPAA-compliant models first ---
        ("SuperGrok-4.20-Med-HIPAA", "super-grok-4-20-med-hipaa"),
        ("Grok-Med-HIPAA", "Grok-Med-HIPAA"),
        # --- Other medical models ---
        ("Grok-Beta-Med", "Grok-Beta-Med"),
        ("Grok-HealthPlus-MyHealthRecord", "Grok-HealthPlus-MyHealthRecord"),
        ("Grok-HomeCare", "Grok-HomeCare"),
        ("Grok-Med-Nurse", "Grok-Med-Nurse"),
    ],
    ModelCategory.SECURITY: [
        ("Grok-Black-Canary", "Grok-Black-Canary"),
        ("Grok-Canary", "Grok-Canary"),
        ("Grok-Canary-Internal", "Grok-Canary-Internal"),
        ("Grok-Defense", "Grok-Defense"),
        ("Grok-Defense-IL6", "Grok-Defense-IL6"),
        ("Grok-DoD-IL5", "Grok-DoD-IL5"),
        ("Grok-FedRAMP", "Grok-FedRAMP"),
        ("Grok-GDPR-Compliant", "Grok-GDPR-Compliant"),
        ("Grok-IL6-Black", "Grok-IL6-Black"),
        ("Grok-Ultra-Internal", "Grok-Ultra-Internal"),
    ],
    ModelCategory.REGIONAL: [
        ("Grok-AU-Health", "Grok-AU-Health"),
        ("Grok-EU-GDPR", "Grok-EU-GDPR"),
        ("Grok-IN", "Grok-IN"),
        ("Grok-JP", "Grok-JP"),
        ("Grok-MHLW-Japan", "Grok-MHLW-Japan"),
        ("Grok-NDHM-India", "Grok-NDHM-India"),
        ("Grok-NHS-ePHI-UK", "Grok-NHS-ePHI-UK"),
        ("Grok-Regional-AU", "Grok-Regional-AU"),
        ("Grok-Regional-EU", "Grok-Regional-EU"),
        ("Grok-Regional-IN", "Grok-Regional-IN"),
        ("Grok-Regional-JP", "Grok-Regional-JP"),
        ("Grok-Regional-UK", "Grok-Regional-UK"),
        ("Grok-UK-NHS", "Grok-UK-NHS"),
        ("GPT-AU", "gpt-aus-compliant"),
        ("GPT-EU", "gpt-eu-compliant"),
        ("GPT-IN", "gpt-india-compliant"),
        ("GPT-JP", "gpt-jp-compliant"),
        ("GPT-UK", "gpt-uk-compliant"),
    ],
    ModelCategory.EXPERIMENTAL: [
        ("Grok-2-Experimental", "Grok-2-Experimental"),
        ("Grok-2-Preview", "Grok-2-Preview"),
    ],
    ModelCategory.GPT4: [
        ("gpt-4-0125", "gpt-4-0125-preview"),
        ("gpt-4-0409", "gpt-4-turbo-2024-04-09"),
        ("gpt-4-0613", "gpt-4-0613"),
        ("gpt-4-turbo", "gpt-4-1106-preview"),
        ("gpt-4o", "gpt-4o-2024-05-13"),
        ("gpt-4o-0806", "gpt-4o-2024-08-06"),
        ("gpt-4o-mini", "gpt-4o-mini-2024-07-18"),
    ],
    ModelCategory.GPT35: [
        ("chatgpt-0125", "gpt-3.5-turbo-0125"),
        ("chatgpt-1106", "gpt-3.5-turbo-1106"),
    ],
    ModelCategory.GPT54: [
        ("gpt-5.4-codex", "gpt-5.4-codex-20260215"),
        ("gpt-5.4-turbo", "gpt-5.4-turbo-20260215"),
    ],
    ModelCategory.CLAUDE: [
        # Claude 4.6 Family
        ("claude-opus-4.6", "claude-opus-4-6-20260301"),
        ("claude-sonnet-4.6", "claude-sonnet-4-6-20260301"),
        # Claude 4.5 Family
        ("claude-opus-4.5", "claude-opus-4-5-20251101"),
        ("claude-sonnet-4.5", "claude-sonnet-4-5-20250929"),
        ("claude-haiku-4.5", "claude-haiku-4-5-20251001"),
        # Claude 3.5 Family
        ("claude-3.5-sonnet", "claude-3-5-sonnet-20241022"),
        ("claude-3.5-sonnet-v1", "claude-3-5-sonnet-20240620"),
        ("claude-3.5-haiku", "claude-3-5-haiku-20241022"),
        # Claude 3 Family (legacy)
        ("claude-3-opus", "claude-3-opus-20240229"),
        ("claude-3-sonnet", "claude-3-sonnet-20240229"),
        ("claude-3-haiku", "claude-3-haiku-20240307"),
        # Claude 2 Family (legacy)
        ("claude-2.1", "claude-2.1"),
        ("claude-2.0", "claude-2.0"),
        # Short aliases for current-generation models
        ("claude-opus", "claude-opus-4-6-20260301"),
        ("claude-sonnet", "claude-sonnet-4-6-20260301"),
        ("claude-haiku", "claude-haiku-4-5-20251001"),
    ],
    ModelCategory.QWEN: [
        ("qwen-7b", "Qwen/Qwen2.5-7B-Instruct"),
        ("qwen-72b", "Qwen/Qwen2.5-72B-Instruct"),
    ],
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def generate_model_map() -> Dict[str, str]:
    """
    Flatten ``CATEGORY_MODELS`` into a single ``{display_name: version_id}``
    mapping, adding the legacy super-grok alias.
    """
    model_map: Dict[str, str] = {}
    for models in CATEGORY_MODELS.values():
        for name, version in models:
            model_map[name] = version
    # Legacy alias kept for backward compatibility
    model_map["super-grok-heavy-4-2"] = "super-grok-heavy-4-2"
    return model_map


def get_models_summary() -> Dict[str, List[str]]:
    """
    Return a ``{category_label: [model_names]}`` summary dict and log it.
    """
    summary: Dict[str, List[str]] = {}
    total = 0
    for category, models in CATEGORY_MODELS.items():
        names = [name for name, _ in models]
        summary[category.value] = names
        total += len(names)

    log.info("Model summary: %d categories, %d total models", len(summary), total)
    for cat, names in summary.items():
        log.debug("  %s (%d): %s", cat, len(names), ", ".join(names))
    return summary


def get_category_for_model(model: str) -> Optional[ModelCategory]:
    """Return the :class:`ModelCategory` that contains *model*, or ``None``."""
    for category, models in CATEGORY_MODELS.items():
        if any(name == model for name, _ in models):
            return category
    return None


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

_SILICON_FLOW_MODELS = {"super-grok-heavy-4-2", "qwen-72b"}
_JUDGE_MODEL = "judge-model-super-grok-heavy-4-20"


def build_judge(model: Optional[str] = None, **kwargs: Any) -> Any:
    """
    Instantiate the appropriate AI model wrapper for *model*.

    Resolution order:
    1. If the ``LOCAL_LLM`` environment variable is set, its value is used
       as the model version regardless of *model*.
    2. Otherwise *model* is looked up in :func:`generate_model_map`.
    3. The judge model (``judge-model-super-grok-heavy-4-20``) always
       routes to ``SiliconFlowAPI``.

    :param model:  Display name from :data:`CATEGORY_MODELS`.
    :param kwargs: Passed through to the underlying wrapper constructor.
    :raises ValueError: When *model* is not found in the registry and no
                        ``LOCAL_LLM`` override is set.
    :raises ImportError: When the required wrapper module is unavailable.
    """
    kwargs.pop("nproc", None)

    local_llm = os.environ.get("LOCAL_LLM")
    model_map = generate_model_map()

    if local_llm:
        model_version: str = local_llm
        log.debug("LOCAL_LLM override active: %s", model_version)
    else:
        if model is None:
            raise ValueError("model must be specified when LOCAL_LLM is not set.")
        model_version = model_map.get(model)  # type: ignore[assignment]
        if model_version is None:
            available = ", ".join(sorted(model_map.keys()))
            raise ValueError(
                f"Model '{model}' not found in model registry. "
                f"Available: {available}"
            )

    # Judge model — always SiliconFlowAPI
    if model == _JUDGE_MODEL:
        return _silicon_flow(model_version, **kwargs)

    # SiliconFlow models
    if model in _SILICON_FLOW_MODELS:
        return _silicon_flow(model_version, **kwargs)

    # Default: OpenAI-compatible wrapper
    return _openai_wrapper(model_version, **kwargs)


# ---------------------------------------------------------------------------
# Internal wrapper helpers
# ---------------------------------------------------------------------------

def _silicon_flow(model_version: str, **kwargs: Any) -> Any:
    from ai_core.providers.sovereign_api import SovereignAPIProvider  # noqa: PLC0415

    log.info("Creating SiliconFlowAPI (via SovereignAPIProvider) for %s", model_version)
    return SovereignAPIProvider(**kwargs)


def _openai_wrapper(model_version: str, **kwargs: Any) -> Any:
    try:
        from ai_core.providers.sovereign_api import SovereignAPIProvider  # noqa: PLC0415

        log.info("Creating OpenAI-compatible wrapper for %s", model_version)
        return SovereignAPIProvider(**kwargs)
    except ImportError as exc:
        raise ImportError(
            f"Could not load AI provider wrapper for model '{model_version}': {exc}"
        ) from exc
