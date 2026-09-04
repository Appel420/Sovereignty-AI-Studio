"""Local coordination spine connecting lanes, leases, conflicts, and evidence.

This module coordinates existing authority components; it does not mint authority,
select providers, modify repositories, or contact the network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .conflict_manager import ConflictManager
from .evidence_adapter import EvidenceAdapter
from .execution_contracts import ExecutionReceipt, RouteDecision
from .lease import LeaseError, LeaseIssuer, LeaseToken
from .local_agent_bus import AgentMessage, LocalAgentBus, BusError
from .task_envelope import TaskEnvelope


@dataclass(frozen=True, slots=True)
class CoordinationOutcome:
    status: str
    task_id: str
    message_id: str | None = None
    lease_id: str | None = None
    conflict: Mapping[str, Any] | None = None
    route: RouteDecision | None = None
    receipt: ExecutionReceipt | None = None
    evidence: Mapping[str, Any] | None = None


class LocalCoordinationSpine:
    """Connect the local bus to scope holds, leases, and evidence sinks."""

    def __init__(
        self,
        bus: LocalAgentBus,
        *,
        conflicts: ConflictManager | None = None,
        leases: LeaseIssuer | None = None,
        evidence: EvidenceAdapter | None = None,
    ) -> None:
        self.bus = bus
        self.conflicts = conflicts or ConflictManager()
        self.leases = leases
        self.evidence = evidence

    def submit(
        self,
        message: AgentMessage,
        envelope: TaskEnvelope,
        *,
        lease: LeaseToken | None = None,
        require_lease: bool = False,
    ) -> CoordinationOutcome:
        if envelope.task_id != message.task_id:
            raise BusError("message and task envelope task ids do not match")
        if envelope.requested_agent and envelope.requested_agent != message.recipient_agent:
            raise BusError("task recipient does not match coordination message")
        if envelope.branch and envelope.branch != message.sender_branch:
            raise BusError("task branch does not match message sender branch")

        conflict = self.conflicts.register(envelope)
        if conflict is not None:
            return CoordinationOutcome(
                status="conflict",
                task_id=envelope.task_id,
                conflict={
                    "task_id": conflict.task_id,
                    "conflicts_with": conflict.conflicts_with,
                    "scope": conflict.scope,
                    "reason": conflict.reason,
                },
            )

        try:
            if require_lease and self.leases is None:
                raise LeaseError("write coordination requires an injected lease issuer")
            if lease is not None:
                if self.leases is None:
                    raise LeaseError("cannot verify lease without an injected lease issuer")
                self.leases.require_for_write(lease, envelope.scope)
                if lease.agent_id != message.sender_agent or lease.branch != message.sender_branch:
                    raise LeaseError("lease identity does not match message sender")
            elif require_lease:
                raise LeaseError("write coordination requires a lease")

            delivery = self.bus.send(message)
            status = str(delivery.get("status", "unknown"))
            route = RouteDecision(
                task_id=envelope.task_id,
                decision="ALLOW",
                route=message.recipient_agent,
                mode=envelope.mode,
                reason_code="LOCAL_COORDINATION_DELIVERED" if status == "delivered" else "LOCAL_COORDINATION_QUEUED",
                policy_hash="local-agent-lanes@1.0.0",
                requires_owner_approval=envelope.requires_owner_approval,
            )
            receipt = ExecutionReceipt(
                task_id=envelope.task_id,
                route=message.recipient_agent,
                mode=envelope.mode,
                status=status,
                decision_hash=_decision_hash(route),
                files_changed=(),
                network_accessed=False,
            )
            evidence = self.evidence.record(receipt, route) if self.evidence is not None else None
            return CoordinationOutcome(
                status=status,
                task_id=envelope.task_id,
                message_id=message.message_id,
                lease_id=lease.lease_id if lease is not None else None,
                route=route,
                receipt=receipt,
                evidence=evidence,
            )
        except Exception:
            self.conflicts.release(envelope.task_id)
            raise

    def release(self, task_id: str) -> None:
        """Release a completed task's scope hold; never changes repository state."""
        self.conflicts.release(task_id)


def _decision_hash(route: RouteDecision) -> str:
    import hashlib
    import json

    encoded = json.dumps(route.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
