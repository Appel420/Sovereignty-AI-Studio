"""Tests for local process, deployment, and commit approval notifications."""
from local_governance.approvals import ApprovalStore
import pytest


def test_pending_requests_are_deduplicated_and_renotified(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.jsonl")
    first = store.request(kind="COMMIT", subject="abc123", summary="Commit runtime fix", requested_by="agent")
    second = store.request(kind="COMMIT", subject="abc123", summary="Commit runtime fix", requested_by="agent")

    assert first["approval_id"] == second["approval_id"]
    assert second["notification_count"] == 2
    assert len(store.list()) == 1


def test_owner_can_approve_and_action_is_audited(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.jsonl")
    request = store.request(kind="DEPLOYMENT", subject="build-7", summary="Deploy local build", requested_by="ci")

    result = store.decide(request["approval_id"], "APPROVED", "owner")

    assert result["state"] == "APPROVED"
    assert result["decided_by"] == "owner"
    assert result["audit"][-1]["event"] == "APPROVAL_APPROVED"


def test_owner_can_hold_without_locking_access(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.jsonl")
    request = store.request(kind="PROCESS", subject="bridge", summary="Start bridge", requested_by="launcher")

    result = store.decide(request["approval_id"], "HELD", "owner")

    assert result["state"] == "HELD"
    assert result["decided_by"] == "owner"
    assert result["audit"][-1]["event"] == "APPROVAL_HELD"


def test_denied_request_cannot_be_decided_again(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.jsonl")
    request = store.request(kind="PROCESS", subject="node-bridge", summary="Start service", requested_by="launcher")
    store.decide(request["approval_id"], "DENIED", "owner")

    with pytest.raises(ValueError, match="already DENIED"):
        store.decide(request["approval_id"], "APPROVED", "owner")


def test_decision_requires_owner(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.jsonl")
    request = store.request(kind="PROCESS", subject="bridge", summary="Start bridge", requested_by="launcher")

    with pytest.raises(ValueError, match="owner is required"):
        store.decide(request["approval_id"], "APPROVED", "")
