"""Integration tests for the local coordination spine."""
import json
from pathlib import Path

import pytest

from backend.coordination.coordination_spine import LocalCoordinationSpine
from backend.coordination.conflict_manager import ConflictManager
from backend.coordination.evidence_adapter import EvidenceAdapter
from backend.coordination.local_agent_bus import AgentMessage, LocalAgentBus
from backend.coordination.task_envelope import TaskEnvelope

POLICY = json.loads((Path(__file__).resolve().parents[2] / "config/agent-lanes.json").read_text())


def message(task_id: str, branch: str = "copilot/main") -> AgentMessage:
    return AgentMessage.create(
        sender_agent="copilot",
        sender_provider="github-copilot",
        sender_branch=branch,
        recipient_agent="grok",
        message_type="task.context",
        task_id=task_id,
        payload={"scope": ["workflow review"]},
    )


def envelope(task_id: str, scope=("workflow review",)) -> TaskEnvelope:
    return TaskEnvelope(
        task_id=task_id,
        requester="Appel420",
        owner="Appel420",
        requested_agent="grok",
        branch="copilot/main",
        scope=scope,
        mode="offline",
    )


def test_spine_delivers_and_emits_bound_receipt_and_evidence():
    delivered = []
    bus = LocalAgentBus(POLICY)
    bus.register("grok", lambda item: delivered.append(item.message_id) or {"ok": True})
    evidence = EvidenceAdapter(append_scar=lambda event: delivered.append(event["receipt_hash"]))
    spine = LocalCoordinationSpine(bus, conflicts=ConflictManager(), evidence=evidence)

    outcome = spine.submit(message("task-spine-1"), envelope("task-spine-1"))

    assert outcome.status == "delivered"
    assert outcome.receipt is not None
    assert outcome.evidence is not None
    assert len(delivered) == 2
    spine.release("task-spine-1")


def test_overlapping_task_is_held_for_review_without_delivery():
    bus = LocalAgentBus(POLICY)
    first = LocalCoordinationSpine(bus, conflicts=ConflictManager())
    first.submit(message("task-spine-2"), envelope("task-spine-2"))
    second = LocalCoordinationSpine(bus, conflicts=first.conflicts)

    outcome = second.submit(message("task-spine-3"), envelope("task-spine-3"))

    assert outcome.status == "conflict"
    assert outcome.conflict["conflicts_with"] == ("task-spine-2",)
    first.release("task-spine-2")


def test_scope_mismatch_is_rejected_before_delivery():
    bus = LocalAgentBus(POLICY)
    bus.register("grok", lambda item: {"ok": True})
    spine = LocalCoordinationSpine(bus)
    bad = envelope("task-spine-4")
    bad = TaskEnvelope(
        task_id=bad.task_id, requester=bad.requester, owner=bad.owner,
        requested_agent=bad.requested_agent, branch="gpt/review", scope=bad.scope,
        mode=bad.mode,
    )
    with pytest.raises(Exception, match="branch"):
        spine.submit(message("task-spine-4"), bad)
