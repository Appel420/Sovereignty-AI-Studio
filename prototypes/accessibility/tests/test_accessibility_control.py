"""Accessibility Control Model v1 — isolated harness tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running without package install: prototypes/ on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from accessibility.confirmation import handle_command  # noqa: E402


def test_safe_action_executes():
    result = handle_command("open my notes")
    assert result["status"] == "EXECUTED"
    assert result["executed"] is True
    assert result.get("action") == "open"


def test_destructive_requires_confirmation():
    result = handle_command("delete notes.txt", pending=False)
    assert result["status"] == "CONFIRM_REQUIRED"
    assert result["executed"] is False
    assert result["action"] == "delete_file"
    assert result["target"] == "notes.txt"


def test_cancel_prevents_execution():
    result = handle_command("cancel")
    assert result["status"] == "CANCELLED"
    assert result["executed"] is False


def test_ambiguous_requires_clarification():
    result = handle_command("remove the thing")
    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert result["executed"] is False


def test_lease_mismatch_denies_deploy():
    result = handle_command(
        "deploy production",
        pending=True,
        lease_scope="development-only",
    )
    assert result["status"] == "DENIED"
    assert result["reason"] == "LEASE_SCOPE_MISMATCH"
    assert result["executed"] is False


def test_confirmed_destructive_action_executes():
    result = handle_command("delete notes.txt", pending=True)
    assert result["status"] == "EXECUTED"
    assert result["executed"] is True
    assert result["action"] == "delete_file"


def test_pending_state_does_not_execute_without_flag():
    result = handle_command("delete notes.txt", pending=False)
    assert result["status"] == "CONFIRM_REQUIRED"
    assert result["executed"] is False


def test_scar_event_schema_is_stable():
    result = handle_command("delete notes.txt")
    scar = result["scar"]
    assert scar["event_type"] == "ACTION_DECISION"
    assert scar["event_class"] == "policy"
    assert scar["metadata"]["interface"] == "voice"
    assert scar["metadata"]["action"] == "delete_file"
    assert scar["metadata"]["risk"] == "destructive"
