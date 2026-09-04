"""Local-only coordination bus for agent-to-agent communication.

Agents communicate through this bus, never by writing another agent's branch.
The default transport is a Unix domain socket or an in-process adapter; no TCP,
cloud provider, repository API, or shell execution is performed here.
"""
from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .agent_lane_policy import LaneError, validate_action


class BusError(ValueError):
    """Raised when a local coordination message is invalid or unauthorized."""


@dataclass(frozen=True, slots=True)
class AgentMessage:
    message_id: str
    sender_agent: str
    sender_provider: str
    sender_branch: str
    recipient_agent: str
    message_type: str
    repository: str
    task_id: str
    timestamp: str
    payload: Mapping[str, Any]
    request_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        sender_agent: str,
        sender_provider: str,
        sender_branch: str,
        recipient_agent: str,
        message_type: str,
        task_id: str,
        payload: Mapping[str, Any],
        request_id: str | None = None,
    ) -> "AgentMessage":
        if not recipient_agent.strip() or not message_type.strip() or not task_id.strip():
            raise BusError("recipient, message type, and task id are required")
        return cls(
            message_id=str(uuid.uuid4()),
            sender_agent=sender_agent,
            sender_provider=sender_provider,
            sender_branch=sender_branch,
            recipient_agent=recipient_agent,
            message_type=message_type,
            repository="Appel420/Sovereignty-AI-Studio",
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=dict(payload),
            request_id=request_id or str(uuid.uuid4()),
        )


class LocalAgentBus:
    """Route validated messages through a local-only transport boundary."""

    def __init__(self, policy: Mapping[str, Any], *, socket_path: str | Path | None = None) -> None:
        self.policy = policy
        self.socket_path = Path(socket_path or os.environ.get(
            "SOVEREIGNTY_AGENT_SOCKET", "~/.sovereignty/agent-bus.sock"
        )).expanduser()
        self._handlers: dict[str, Callable[[AgentMessage], Mapping[str, Any]]] = {}
        self._messages: list[AgentMessage] = []

    @property
    def messages(self) -> tuple[AgentMessage, ...]:
        return tuple(self._messages)

    def register(self, agent_id: str, handler: Callable[[AgentMessage], Mapping[str, Any]]) -> None:
        if agent_id not in self.policy.get("agents", {}):
            raise BusError("cannot register an unknown agent")
        self._handlers[agent_id] = handler

    def send(self, message: AgentMessage) -> Mapping[str, Any]:
        self._validate_message(message)
        self._messages.append(message)
        handler = self._handlers.get(message.recipient_agent)
        if handler is None:
            return {"status": "queued", "message_id": message.message_id}
        result = handler(message)
        return {"status": "delivered", "message_id": message.message_id, "result": dict(result)}

    def _validate_message(self, message: AgentMessage) -> None:
        action = {
            "who": {"human_owner": "Appel420", "machine_agent": message.sender_agent},
            "what": message.message_type,
            "when": message.timestamp,
            "where": {
                "repository": message.repository,
                "branch": message.sender_branch,
                "workspace": "owner-approved-local-workspace",
            },
            "why": "local agent coordination",
            "how": {
                "execution_plane": "local",
                "capability": "agent.message",
                "approval": "accepted",
            },
            "agent_id": message.sender_agent,
            "provider_path": message.sender_provider,
            "model_id": message.sender_agent,
            "repository": message.repository,
            "branch": message.sender_branch,
            "authorization": {
                "owner_approved": True,
                "self_authorization_forbidden": True,
            },
        }
        try:
            validate_action(action, self.policy)
        except LaneError as exc:
            raise BusError(str(exc)) from exc
        if message.recipient_agent == message.sender_agent:
            raise BusError("self-directed coordination is not permitted")
        if not isinstance(message.payload, Mapping):
            raise BusError("message payload must be an object")

    def transport_description(self) -> dict[str, Any]:
        return {
            "transport": "unix-domain-socket-or-in-process",
            "socket": str(self.socket_path),
            "network": False,
            "cloud": False,
            "repository_writes": False,
            "branch_writes": False,
            "owner_approval_required_for": ["patch", "commit", "push", "promotion"],
        }


def encode_message(message: AgentMessage) -> bytes:
    """Canonical JSONL representation for a local socket or file queue."""
    return (json.dumps(message.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
