"""Human/machine notification boundary.

The adapter translates an already-authoritative execution event into text,
voice, and machine notifications. It cannot authorize or execute work.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .communication_contracts import CommunicationEvent
from .execution_contracts import ExecutionReceipt, RouteDecision


class CommunicationAdapter:
    """Fan out one canonical execution event to permitted notification channels."""

    def __init__(
        self,
        *,
        publish_text: Callable[[str], Any] | None = None,
        publish_voice: Callable[[str], Any] | None = None,
        publish_machine: Callable[[Mapping[str, Any]], Any] | None = None,
    ) -> None:
        self._publish_text = publish_text
        self._publish_voice = publish_voice
        self._publish_machine = publish_machine

    def publish(self, event: CommunicationEvent) -> None:
        """Publish the same canonical event through all configured channels."""
        if "text" in event.channels and self._publish_text is not None:
            self._publish_text(event.human_text())
        if "voice" in event.channels and self._publish_voice is not None:
            self._publish_voice(event.voice_text())
        if "machine" in event.channels and self._publish_machine is not None:
            self._publish_machine(event.machine_payload())

    def execution_event(
        self,
        *,
        task_id: str,
        requester: str,
        receipt: ExecutionReceipt,
        route: RouteDecision,
        evidence: tuple[str, ...] = (),
        next_action: str | None = None,
    ) -> CommunicationEvent:
        """Build an observational event from an existing route and receipt."""
        if task_id != receipt.task_id or task_id != route.task_id:
            raise ValueError("task identifiers must match")
        if route.decision != "ALLOW":
            raise PermissionError("communication cannot represent unauthorized execution")

        return CommunicationEvent(
            event_id=f"exec-{receipt.task_id}-{receipt.receipt_hash.split(':', 1)[-1][:16]}",
            task_id=task_id,
            who=requester,
            what=f"Execute authorized route '{receipt.route}'",
            when=receipt.timestamp,
            where="local DevAssist execution boundary",
            why=route.reason_code,
            how=f"mode={receipt.mode}; policy={route.policy_hash}",
            status=receipt.status,
            authority="Sovereignty authority decision",
            authorization="ALLOW",
            execution=f"route={receipt.route}",
            result=f"files_changed={len(receipt.files_changed)}; network_accessed={receipt.network_accessed}",
            evidence=evidence,
            next_action=next_action,
        )
