"""Tests for local agent communication and lane isolation."""
import json
from pathlib import Path

import pytest

from backend.coordination.local_agent_bus import AgentMessage, BusError, LocalAgentBus, encode_message

POLICY = json.loads((Path(__file__).resolve().parents[2] / "config/agent-lanes.json").read_text())


def test_message_is_local_and_delivered_only_to_recipient():
    bus = LocalAgentBus(POLICY)
    received = []
    bus.register("grok", lambda message: received.append(message.message_id) or {"ok": True})
    message = AgentMessage.create(
        sender_agent="copilot",
        sender_provider="github-copilot",
        sender_branch="copilot/main",
        recipient_agent="grok",
        message_type="task.context",
        task_id="task-1",
        payload={"scope": ["workflow review"]},
    )
    result = bus.send(message)
    assert result["status"] == "delivered"
    assert received == [message.message_id]
    assert bus.transport_description()["network"] is False


def test_unregistered_recipient_is_queued_without_execution():
    bus = LocalAgentBus(POLICY)
    message = AgentMessage.create(
        sender_agent="claude",
        sender_provider="anthropic-claude",
        sender_branch="claude/review",
        recipient_agent="gpt",
        message_type="review.request",
        task_id="task-2",
        payload={"files": ["README.md"]},
    )
    assert bus.send(message)["status"] == "queued"


def test_cross_lane_sender_is_rejected():
    bus = LocalAgentBus(POLICY)
    message = AgentMessage.create(
        sender_agent="grok",
        sender_provider="github-copilot",
        sender_branch="copilot/main",
        recipient_agent="claude",
        message_type="task.context",
        task_id="task-3",
        payload={},
    )
    with pytest.raises(BusError, match="provider path"):
        bus.send(message)


def test_agents_cannot_send_to_themselves():
    bus = LocalAgentBus(POLICY)
    message = AgentMessage.create(
        sender_agent="copilot",
        sender_provider="github-copilot",
        sender_branch="copilot/main",
        recipient_agent="copilot",
        message_type="task.context",
        task_id="task-4",
        payload={},
    )
    with pytest.raises(BusError, match="self-directed"):
        bus.send(message)


def test_wire_format_is_canonical_jsonl():
    bus = LocalAgentBus(POLICY)
    message = AgentMessage.create(
        sender_agent="gpt",
        sender_provider="openai-gpt",
        sender_branch="gpt/review",
        recipient_agent="copilot",
        message_type="review.result",
        task_id="task-5",
        payload={"b": 2, "a": 1},
    )
    decoded = json.loads(encode_message(message))
    assert decoded["payload"] == {"a": 1, "b": 2}
