"""Tests for device-local issue suggestion deduplication and owner decisions."""
from __future__ import annotations

import json

import pytest

from local_governance.issue_suggestions import IssueSuggestionStore


def observe(store: IssueSuggestionStore, reason: str = "health probe blocked") -> dict:
    return store.observe(
        category="blocked_activity",
        reason=reason,
        title="Background activity blocked",
        evidence="GET /health was blocked by offline policy",
        source="node-bridge",
        component="health_probe",
        target="127.0.0.1:8002/health",
        mode="ghost",
    )


def test_repeated_observations_are_deduplicated(tmp_path):
    store = IssueSuggestionStore(tmp_path / "suggestions.jsonl")
    first = observe(store)
    second = observe(store)

    assert first["suggestion_id"] == second["suggestion_id"]
    assert second["occurrences"] == 2
    assert len(store.list()) == 1


def test_different_causes_create_separate_suggestions(tmp_path):
    store = IssueSuggestionStore(tmp_path / "suggestions.jsonl")
    first = observe(store, "health probe blocked")
    second = observe(store, "websocket upgrade blocked")

    assert first["suggestion_id"] != second["suggestion_id"]
    assert len(store.list()) == 2


def test_owner_decision_is_explicit_and_audited(tmp_path):
    store = IssueSuggestionStore(tmp_path / "suggestions.jsonl")
    suggestion = observe(store)

    accepted = store.decide(suggestion["suggestion_id"], "ACCEPTED")

    assert accepted["state"] == "ACCEPTED"
    assert accepted["owner_decision"] == "ACCEPTED"
    assert accepted["audit"][-1]["event"] == "ISSUE_SUGGESTION_ACCEPTED"
    assert accepted["audit"][-1]["owner_action"] is True


def test_state_persists_locally(tmp_path):
    path = tmp_path / "suggestions.jsonl"
    store = IssueSuggestionStore(path)
    suggestion = observe(store)
    store.decide(suggestion["suggestion_id"], "DECLINED")

    restored = IssueSuggestionStore(path)
    result = restored.list()[0]
    assert result["state"] == "DECLINED"
    assert json.loads(path.read_text(encoding="utf-8"))["suggestion_id"] == result["suggestion_id"]


def test_invalid_decision_is_rejected(tmp_path):
    store = IssueSuggestionStore(tmp_path / "suggestions.jsonl")
    suggestion = observe(store)

    with pytest.raises(ValueError):
        store.decide(suggestion["suggestion_id"], "AUTO_FIX")
