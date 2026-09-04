"""Tests for generalized agent/provider/branch separation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from backend.coordination.agent_lane_policy import LaneError, validate_action

POLICY = json.loads((Path(__file__).resolve().parents[2] / "config/agent-lanes.json").read_text())

def make(agent="copilot", branch="copilot/fix"):
    provider = POLICY["agents"][agent]["provider_path"]
    return {
        "who": {"human_owner": "Appel420", "machine_agent": agent},
        "what": "run local validation", "when": datetime.now(timezone.utc).isoformat(),
        "where": {"repository": POLICY["repository"], "branch": branch, "workspace": "owner-approved"},
        "why": "owner-approved maintenance", "how": {"execution_plane": "local", "capability": "repo.test", "approval": "accepted"},
        "agent_id": agent, "provider_path": provider, "model_id": agent,
        "repository": POLICY["repository"], "branch": branch,
        "authorization": {"owner_approved": True, "self_authorization_forbidden": True},
    }

def test_all_registered_agents_have_separate_lanes():
    for agent in POLICY["agents"]:
        validate_action(make(agent, f"{agent}/validation"), POLICY)

def test_cross_lane_provider_is_denied():
    value = make("grok", "grok/validation")
    value["provider_path"] = "github-copilot"
    with pytest.raises(LaneError): validate_action(value, POLICY)

def test_cross_lane_branch_is_denied():
    with pytest.raises(LaneError): validate_action(make("claude", "grok/validation"), POLICY)

def test_protected_branch_is_denied():
    with pytest.raises(LaneError): validate_action(make("copilot", "copilot/main"), POLICY)

def test_write_requires_accepted_approval():
    value = make(); value["how"]["approval"] = "pending"
    with pytest.raises(LaneError): validate_action(value, POLICY, write=True)
