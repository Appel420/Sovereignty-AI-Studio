"""Tests for Shortcut Flow to Gate/Genesis routing."""
from __future__ import annotations

import pytest

from backend.coordination.shortcut_router import ShortcutRouter, classify_prompt


def document(prompt: str = "Fix the repository code") -> dict:
    return {
        "request": {
            "request_id": "req-1",
            "prompt": prompt,
            "permissions": {
                "device_access": False,
                "memory_access": False,
                "external_models": True,
            },
            "routing_decision": {"judge_required": True},
        }
    }


def allow(_task, _request):
    return {"decision": "OWNER_AUTHORIZED", "policy_hash": "sha256:policy"}


def test_classification_precedence_prefers_coding() -> None:
    assert classify_prompt("Analyze this repository and summarize the code") == "CODING"


def test_shortcut_router_creates_task_and_route_without_execution() -> None:
    result = ShortcutRouter(allow).route(document())
    assert result.task.task_id == "req-1"
    assert result.task.mode == "online"
    assert result.task_type == "CODING"
    assert result.route is not None
    assert result.route.route == "sovereignty-runtime"


def test_memory_permission_is_not_granted_by_router() -> None:
    result = ShortcutRouter(allow).route(document())
    assert "memory" not in result.task.scope


def test_denied_gate_returns_escalation_and_no_route() -> None:
    def deny(_task, _request):
        return {"decision": "DENY", "reason_code": "POLICY_DENIED", "policy_hash": "sha256:p"}

    result = ShortcutRouter(deny).route(document())
    assert result.route is None
    assert result.escalation is not None
    assert result.escalation.reason_code == "POLICY_DENIED"


def test_missing_request_id_fails_closed() -> None:
    payload = document()
    payload["request"].pop("request_id")
    with pytest.raises(ValueError, match="request_id"):
        ShortcutRouter(allow).route(payload)
