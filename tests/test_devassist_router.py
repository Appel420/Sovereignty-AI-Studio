"""Tests for branch-aware, non-destructive council routing."""
from __future__ import annotations

import pytest

from backend.coordination import DevAssistRouter, TaskEnvelope


def test_routes_security_to_ara_branch() -> None:
    router = DevAssistRouter()
    task = router.classify(
        task_id="security-1",
        requester="owner",
        owner="Appel420",
        scope=("security",),
    )
    result = router.route(task)
    assert result.approved is True
    assert result.routes[0].branch == "ara-hardened"


def test_non_overlapping_tasks_can_run_in_parallel() -> None:
    router = DevAssistRouter()
    first = router.classify(
        task_id="ui-1", requester="owner", owner="Appel420", scope=("usability",)
    )
    second = router.classify(
        task_id="api-1", requester="owner", owner="Appel420", scope=("integration",)
    )
    assert router.route(first).approved is True
    assert router.route(second).approved is True


def test_overlapping_tasks_wait_for_council_without_mutation() -> None:
    router = DevAssistRouter()
    first = router.classify(
        task_id="api-1", requester="owner", owner="Appel420", scope=("integration",)
    )
    second = router.classify(
        task_id="api-2", requester="owner", owner="Appel420", scope=("integration",)
    )
    assert router.route(first).approved is True
    conflict = router.route(second)
    assert conflict.approved is False
    assert conflict.conflicts[0].status == "pending-council-review"
    assert router.conflicts.active()[0].task_id == "api-1"


def test_main_is_never_a_writable_agent_branch() -> None:
    with pytest.raises(ValueError, match="main"):
        TaskEnvelope("main-1", "owner", "Appel420", branch="main")


def test_unknown_branch_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown agent branch"):
        DevAssistRouter().classify(
            task_id="bad-1",
            requester="owner",
            owner="Appel420",
            branch="does-not-exist",
            scope=("integration",),
        )
