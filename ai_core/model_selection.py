"""
AI model selection & routing helpers.

This module centralizes:
- Normalization of model identifiers across providers (Claude/GPT/Grok/Qwen)
- On-device model selection via local GGUF/ONNX paths (no external SaaS required)
- Judge-model routing helpers (for eval/scoring style tasks)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterable, Optional


class ModelSelectionError(RuntimeError):
    pass


class UnknownModelError(ModelSelectionError):
    def __init__(self, model_id: str, *, suggestions: Iterable[str] = ()):
        suggestion_text = ""
        suggestions = list(suggestions)
        if suggestions:
            suggestion_text = f" Did you mean: {', '.join(suggestions[:8])}?"
        super().__init__(f"Unknown model_id={model_id!r}.{suggestion_text}")


def _sanitize_env_suffix(value: str) -> str:
    # SOVEREIGN_MODEL_PATH_<SUFFIX> env vars are commonly used for per-model paths.
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


@dataclass(frozen=True)
class ModelSelection:
    model_id: str
    family: str
    backend: str
    is_judge: bool = False
    local_path: Optional[str] = None

    def model_path_env(self) -> str:
        return f"SOVEREIGN_MODEL_PATH_{_sanitize_env_suffix(self.model_id)}"


_KNOWN_MODEL_IDS = (
    # Anthropic
    "claude-haiku",
    "claude-sonnet",
    "claude-opus",
    # OpenAI
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    # xAI
    "grok-4-3",
    "grok-4-3-mini",
    "grok-4-2",
    # Qwen (typically on-device / self-hosted)
    "qwen-7b",
    "qwen-72b",
    # Judge / routing
    "sgh-judge",
)


def known_models() -> list[str]:
    return list(_KNOWN_MODEL_IDS)


def is_judge_model(model_id: str) -> bool:
    mid = normalize_model_id(model_id)
    return (
        mid == "sgh-judge"
        or "judge" in mid
        or mid.endswith("-judge")
        or mid.startswith("judge-")
    )


def normalize_model_id(model_id: str) -> str:
    return (model_id or "").strip().lower()


def suggest_models(prefix: str, *, limit: int = 8) -> list[str]:
    p = normalize_model_id(prefix)
    if not p:
        return []
    matches = [m for m in _KNOWN_MODEL_IDS if m.startswith(p)]
    return matches[:limit]


def _infer_family_backend(model_id: str) -> tuple[str, str]:
    mid = normalize_model_id(model_id)
    if mid.startswith("claude-"):
        return "claude", "cloud_anthropic"
    if mid.startswith("gpt-"):
        return "gpt", "cloud_openai"
    if mid.startswith("grok-"):
        return "grok", "cloud_xai"
    if mid.startswith("qwen-") or mid.startswith("qwen/"):
        return "qwen", "local"
    if mid == "sgh-judge":
        return "judge", "local"
    return "unknown", "unknown"


def resolve_local_model_path(model_id: str) -> Optional[str]:
    """
    Resolve an on-device model path for a model id.

    Precedence:
    1) SOVEREIGN_MODEL_PATH_<MODEL_ID> (sanitized)
    2) SOVEREIGN_MODEL_PATH
    """
    mid = normalize_model_id(model_id)
    if not mid:
        return None

    per_model_env = f"SOVEREIGN_MODEL_PATH_{_sanitize_env_suffix(mid)}"
    return os.getenv(per_model_env) or os.getenv("SOVEREIGN_MODEL_PATH")


def select_model(model_id: str, *, task: str = "chat") -> ModelSelection:
    """
    Select a model and attach routing hints.

    `task` can be:
    - "chat": normal conversation/inference
    - "judge": evaluation/scoring (routes to a judge model when possible)
    """
    requested = normalize_model_id(model_id)
    if not requested:
        raise ModelSelectionError("model_id is required")

    effective = requested
    if task == "judge" and not is_judge_model(requested):
        effective = normalize_model_id(os.getenv("SOVEREIGN_JUDGE_MODEL", "sgh-judge"))

    family, backend = _infer_family_backend(effective)

    # If it looks like a known provider model but isn't in our known list,
    # accept it anyway (we only use it for routing hints).
    known_or_providerish = (
        effective in _KNOWN_MODEL_IDS
        or effective.startswith(("claude-", "gpt-", "grok-", "qwen-"))
        or effective in ("sgh-judge",)
    )
    if not known_or_providerish:
        raise UnknownModelError(effective, suggestions=suggest_models(effective))

    local_path = resolve_local_model_path(effective) if backend == "local" else None
    return ModelSelection(
        model_id=effective,
        family=family,
        backend=backend,
        is_judge=is_judge_model(effective),
        local_path=local_path,
    )

