"""Contract tests for the existing local DevAssist execution boundary."""
from __future__ import annotations

import pytest

from backend.coordination.devassist_adapter import DevAssistExecutionAdapter
from backend.coordination.execution_contracts import RouteDecision
from backend.coordination.task_envelope import TaskEnvelope


def task() -> TaskEnvelope:
    return TaskEnvelope(
        task_id="task-1",
        requester="owner",
        owner="Appel420",
        branch="copilot",
        scope=("code-assistance",),
        mode="offline",
    )


def route(*, route: str = "devassist", decision: str = "ALLOW") -> RouteDecision:
    return RouteDecision(
        task_id="task-1",
        decision=decision,
        route=route,
        mode="offline",
        reason_code="ROUTE_AUTHORIZED",
        policy_hash="sha256:policy",
        timestamp="2026-08-04T00:00:00Z",
    )


def test_devassist_requires_authorized_route() -> None:
    adapter = DevAssistExecutionAdapter(lambda _task, _route: {"status": "ok"})

    with pytest.raises(AttributeError):
        adapter.execute(task(), None)  # type: ignore[arg-type]


def test_devassist_rejects_non_allow_route() -> None:
    adapter = DevAssistExecutionAdapter(lambda _task, _route: {"status": "ok"})

    with pytest.raises(PermissionError, match="ALLOW"):
        adapter.execute(task(), route(decision="DENY"))


def test_devassist_rejects_external_route() -> None:
    adapter = DevAssistExecutionAdapter(
        lambda _task, _route: {"status": "ok"},
        allowed_routes={"devassist"},
    )

    with pytest.raises(PermissionError, match="not enabled"):
        adapter.execute(task(), route(route="sovereignty-runtime"))


def test_devassist_returns_execution_receipt() -> None:
    adapter = DevAssistExecutionAdapter(
        lambda received_task, received_route: {
            "status": "COMPLETED",
            "output_hash": "sha256:output",
            "files_changed": ["example.py"],
            "network_accessed": False,
            "same_task": received_task.task_id == received_route.task_id,
        }
    )

    receipt = adapter.execute(task(), route())

    assert receipt.task_id == "task-1"
    assert receipt.route == "devassist"
    assert receipt.mode == "offline"
    assert receipt.status == "COMPLETED"
    assert receipt.output_hash == "sha256:output"
    assert receipt.files_changed == ("example.py",)
    assert receipt.network_accessed is False


def test_devassist_does_not_execute_when_route_is_rejected() -> None:
    executed = False

    def executor(_task, _route):
        nonlocal executed
        executed = True
        return {"status": "ok"}

    adapter = DevAssistExecutionAdapter(executor)

    with pytest.raises(PermissionError):
        adapter.execute(task(), route(decision="ESCALATE"))

    assert executed is False
