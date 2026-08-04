"""Focused tests for the local coordination contract boundary."""
from __future__ import annotations

import pytest

from backend.coordination.execution_contracts import (
    ExecutionReceipt,
    HumanEscalationEvent,
    RouteDecision,
    make_scar_event,
)


def test_route_decision_rejects_invalid_mode() -> None:
    with pytest.raises(ValueError, match="unsupported mode"):
        RouteDecision("task-1", "ALLOW", "devassist", "cloud", "ok", "sha256:policy")


def test_offline_receipt_cannot_report_network_access() -> None:
    with pytest.raises(ValueError, match="offline execution"):
        ExecutionReceipt(
            "task-1",
            "devassist",
            "offline",
            "COMPLETED",
            "sha256:decision",
            network_accessed=True,
        )


def test_receipt_hash_is_deterministic_for_fixed_timestamp() -> None:
    first = ExecutionReceipt(
        "task-1",
        "devassist",
        "offline",
        "COMPLETED",
        "sha256:decision",
        timestamp="2026-08-02T00:00:00Z",
    )
    second = ExecutionReceipt(
        "task-1",
        "devassist",
        "offline",
        "COMPLETED",
        "sha256:decision",
        timestamp="2026-08-02T00:00:00Z",
    )
    assert first.receipt_hash == second.receipt_hash


def test_scar_event_contains_only_binding_metadata() -> None:
    event = make_scar_event(
        task_id="task-1",
        event="EXECUTION_RECEIPT",
        route="devassist",
        mode="offline",
        decision="ALLOW",
        policy_hash="sha256:policy",
        receipt_hash="sha256:receipt",
    )
    assert event["event_hash"].startswith("sha256:")
    assert "payload" not in event
    assert "credentials" not in event


def test_escalation_status_is_explicit() -> None:
    event = HumanEscalationEvent("task-1", "OWNER_APPROVAL_REQUIRED", ("backend/",))
    assert event.to_dict()["status"] == "PENDING"
