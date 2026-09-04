"""Fail-closed multi-agent repository and branch-lane validation."""
from __future__ import annotations

import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

REPOSITORY = "Appel420/Sovereignty-AI-Studio"
POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "agent-lanes.json"
REQUIRED = {"who", "what", "when", "where", "why", "how", "agent_id", "provider_path", "model_id", "repository", "branch", "authorization"}


class LaneError(ValueError):
    """Raised when an action is missing provenance or crosses an agent lane."""


def validate_action(action: Mapping[str, Any], policy: Mapping[str, Any], *, write: bool = False) -> None:
    missing = sorted(REQUIRED - set(action))
    if missing:
        raise LaneError(f"missing 5W1H fields: {', '.join(missing)}")
    if action.get("repository") != REPOSITORY or action.get("where", {}).get("repository") != REPOSITORY:
        raise LaneError("repository is outside the owner-approved Studio repository")
    agent_id = action.get("agent_id")
    agent = policy.get("agents", {}).get(agent_id)
    if not isinstance(agent, Mapping):
        raise LaneError("unknown execution agent")
    if action.get("provider_path") != agent.get("provider_path"):
        raise LaneError("provider path does not match selected agent")
    branch = action.get("branch")
    if action.get("where", {}).get("branch") != branch or not fnmatch.fnmatch(branch, agent.get("branch_pattern", "")):
        raise LaneError("branch does not belong to selected agent")
    if branch in set(policy.get("protected_branches", ())):
        raise LaneError("protected branch is not agent-writable")
    try:
        datetime.fromisoformat(str(action["when"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise LaneError("when must be an ISO-8601 timestamp") from exc
    authorization = action.get("authorization", {})
    if authorization.get("self_authorization_forbidden") is not True:
        raise LaneError("self-authorization must remain forbidden")
    if authorization.get("owner_approved") is not True:
        raise LaneError("owner approval is required")
    if write and action.get("how", {}).get("approval") != "accepted":
        raise LaneError("state-changing action requires accepted approval")
