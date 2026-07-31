"""Tests for legacy adapters and command-bus ownership enforcement."""
from backend.coordination.compat import legacy_route_metadata


def test_legacy_router_gets_branch_metadata_without_changing_provider_api() -> None:
    result = legacy_route_metadata(
        task_id="legacy-1",
        requester="legacy-router",
        scope=("integration",),
    )
    assert result["branch"] == "gpt"
    assert result["approved"] is True
    assert result["requires_owner_approval"] is True
