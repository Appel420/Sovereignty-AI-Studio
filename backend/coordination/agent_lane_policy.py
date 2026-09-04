"""Fail-closed multi-agent provenance and lane validation."""
from __future__ import annotations

import fnmatch
from datetime import datetime
from typing import Any, Mapping

REPOSITORY = "Appel420/Sovereignty-AI-Studio"
REQUIRED = {"who", "what", "when", "where", "why", "how", "agent_id", "provider_path", "model_id", "repository", "branch", "authorization"}


class LaneError(ValueError):
    """Raised when provenance is missing or an action crosses an agent lane."""


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LaneError(f"{field} must be an object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LaneError(f"{field} must be a non-empty string")
    return value.strip()


def validate_action(action: Mapping[str, Any], policy: Mapping[str, Any], *, write: bool = False) -> None:
    if not isinstance(action, Mapping):
        raise LaneError("action must be an object")
    missing = sorted(REQUIRED - set(action))
    if missing:
        raise LaneError(f"missing 5W1H fields: {', '.join(missing)}")

    repository = _text(action.get("repository"), "repository")
    where = _mapping(action.get("where"), "where")
    if repository != REPOSITORY or _text(where.get("repository"), "where.repository") != repository:
        raise LaneError("repository is outside the owner-approved Studio repository")

    agent_id = _text(action.get("agent_id"), "agent_id")
    agents = _mapping(policy.get("agents"), "agents")
    agent = _mapping(agents.get(agent_id), f"agents.{agent_id}")
    provider = _text(action.get("provider_path"), "provider_path")
    if provider != _text(agent.get("provider_path"), f"agents.{agent_id}.provider_path"):
        raise LaneError("provider path does not match selected agent")

    who = _mapping(action.get("who"), "who")
    if _text(who.get("machine_agent"), "who.machine_agent") != _text(agent.get("display_name"), f"agents.{agent_id}.display_name"):
        raise LaneError("machine identity does not match selected agent")

    model_id = _text(action.get("model_id"), "model_id")
    active_model = agent.get("active_model")
    if isinstance(active_model, str) and model_id != active_model:
        raise LaneError("model label does not match the selected agent's active model")

    branch = _text(action.get("branch"), "branch")
    if _text(where.get("branch"), "where.branch") != branch:
        raise LaneError("branch does not match the 5W1H location")
    pattern = _text(agent.get("branch_pattern"), f"agents.{agent_id}.branch_pattern")
    if not fnmatch.fnmatchcase(branch, pattern):
        raise LaneError("branch does not belong to selected agent")
    if branch in set(policy.get("protected_branches", ())):
        raise LaneError("protected branch is not agent-writable")

    _text(action.get("what"), "what")
    _text(action.get("why"), "why")
    how = _mapping(action.get("how"), "how")
    _text(how.get("execution_plane"), "how.execution_plane")
    try:
        timestamp = datetime.fromisoformat(_text(action.get("when"), "when").replace("Z", "+00:00"))
    except ValueError as exc:
        raise LaneError("when must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None:
        raise LaneError("when must include timezone information")

    authorization = _mapping(action.get("authorization"), "authorization")
    if authorization.get("self_authorization_forbidden") is not True:
        raise LaneError("self-authorization must remain forbidden")
    if authorization.get("owner_approved") is not True:
        raise LaneError("owner approval is required")
    if write and how.get("approval") != "accepted":
        raise LaneError("state-changing action requires accepted approval")
