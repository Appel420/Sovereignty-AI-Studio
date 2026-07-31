"""Compatibility helpers for legacy routers.

Legacy provider routers retain their public APIs and provider behavior. They use
this module only to obtain a branch-aware coordination decision, so routing
ownership is centralized without forcing every caller to construct envelopes.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .devassist_router import DevAssistRouter


def legacy_route_metadata(
    *,
    task_id: str,
    requester: str,
    owner: str = "Appel420",
    scope: Iterable[str] = (),
    requested_agent: str | None = None,
    branch: str | None = None,
    mode: str = "offline",
) -> dict[str, Any]:
    """Return coordination metadata while preserving legacy provider APIs."""
    router = DevAssistRouter()
    envelope = router.classify(
        task_id=task_id,
        requester=requester,
        owner=owner,
        scope=scope,
        requested_agent=requested_agent,
        branch=branch,
        mode=mode,
    )
    result = router.route(envelope)
    router.release(envelope.task_id)
    return {
        "task_id": envelope.task_id,
        "branch": envelope.branch,
        "scope": list(envelope.scope),
        "approved": result.approved,
        "requires_owner_approval": result.requires_owner_approval,
        "conflicts": [conflict.task_id for conflict in result.conflicts],
    }
