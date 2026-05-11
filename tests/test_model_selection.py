from __future__ import annotations

import os

import pytest

from ai_core.model_selection import (
    UnknownModelError,
    is_judge_model,
    select_model,
    suggest_models,
)


def test_is_judge_model() -> None:
    assert is_judge_model("sgh-judge") is True
    assert is_judge_model("judge-grok") is True
    assert is_judge_model("grok-4-3-judge") is True
    assert is_judge_model("grok-4-3") is False


def test_suggest_models() -> None:
    assert "gpt-4o" in suggest_models("gpt-")
    assert suggest_models("") == []


def test_select_model_routes_judge_task() -> None:
    os.environ.pop("SOVEREIGN_JUDGE_MODEL", None)
    sel = select_model("grok-4-3", task="judge")
    assert sel.is_judge is True
    assert sel.model_id == "sgh-judge"


def test_select_model_unknown() -> None:
    with pytest.raises(UnknownModelError):
        select_model("definitely-not-a-model", task="chat")

