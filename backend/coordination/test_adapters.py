"""Adapter-boundary tests for Genesis, DevAssist, and evidence."""
from __future__ import annotations

import pytest

from backend.coordination.devassist_adapter import DevAssistExecutionAdapter
from backend.coordination.evidence_adapter import EvidenceAdapter
from backend.coordination.genesis_adapter import GenesisRouterAdapter
from backend.coordination.task_envelope import TaskEnvelope


def task(mode: str = "offline") -> TaskEnvelope:
    return TaskEnvelope("task-1", "owner", "owner", scope=("repo/",), mode=mode)


def approved(mode: str = "offline") -> dict[str, str]:
    return {"decision": "OWNER_AUTHORIZED", "policy_hash": "sha256:policy"}


def test_genesis_does_not_route_denied_work() -> None:
    with pytest.raises(PermissionError):
        GenesisRouterAdapter().decide(task(), {"decision": "DENY", "policy_hash": "sha256:p"})


def test_genesis_routes_by_mode_without_executing() -> None:
    route = GenesisRouterAdapter().decide(task(), approved())
    assert route.route == "devassist"
    assert route.decision == "ALLOW"


def test_devassist_requires_authorized_local_route() -> None:
    adapter = DevAssistExecutionAdapter(lambda _task, _route: {"status": "COMPLETED"})
    route = GenesisRouterAdapter().decide(task(), approved())
    receipt = adapter.execute(task(), route)
    assert receipt.status == "COMPLETED"
    assert receipt.network_accessed is False


def test_devassist_rejects_scope_or_route_mismatch() -> None:
    adapter = DevAssistExecutionAdapter(lambda _task, _route: {"status": "COMPLETED"})
    route = GenesisRouterAdapter().decide(task(), approved())
    other = TaskEnvelope("task-2", "owner", "owner", mode="offline")
    with pytest.raises(ValueError, match="task_id"):
        adapter.execute(other, route)


def test_evidence_adapter_delegates_to_existing_stores() -> None:
    scar_events: list[dict] = []
    repmhl_records: list[dict] = []
    adapter = DevAssistExecutionAdapter(lambda _task, _route: {"status": "COMPLETED"})
    route = GenesisRouterAdapter().decide(task(), approved())
    receipt = adapter.execute(task(), route)
    event = EvidenceAdapter(
        append_scar=scar_events.append,
        record_repmhl=repmhl_records.append,
    ).record(receipt, route)
    assert scar_events == [event]
    assert repmhl_records[0]["receipt_hash"] == receipt.receipt_hash
