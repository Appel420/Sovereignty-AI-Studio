"""Evidence adapter for existing SCAR and REPMHL implementations.

This module owns no ledger. Callers inject append/handoff functions belonging to
the existing authority and memory layers.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .execution_contracts import ExecutionReceipt, RouteDecision, make_scar_event


class EvidenceAdapter:
    """Bind receipts to existing SCAR and REPMHL stores without owning them."""

    def __init__(
        self,
        *,
        append_scar: Callable[[dict[str, Any]], Any] | None = None,
        record_repmhl: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self._append_scar = append_scar
        self._record_repmhl = record_repmhl

    def record(self, receipt: ExecutionReceipt, route: RouteDecision) -> dict[str, Any]:
        if receipt.task_id != route.task_id:
            raise ValueError("receipt and route task_id do not match")
        if receipt.mode != route.mode:
            raise ValueError("receipt and route modes do not match")
        if route.decision != "ALLOW":
            raise PermissionError("evidence requires an ALLOW route decision")

        event = make_scar_event(
            task_id=receipt.task_id,
            event="EXECUTION_RECEIPT",
            route=receipt.route,
            mode=receipt.mode,
            decision=route.decision,
            policy_hash=route.policy_hash,
            receipt_hash=receipt.receipt_hash,
        )
        if self._append_scar is not None:
            self._append_scar(event)
        if self._record_repmhl is not None:
            self._record_repmhl(
                {
                    "task_id": receipt.task_id,
                    "receipt_hash": receipt.receipt_hash,
                    "event_hash": event["event_hash"],
                    "route": receipt.route,
                    "mode": receipt.mode,
                }
            )
        return event
