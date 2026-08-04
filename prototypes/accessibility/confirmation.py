"""Accessibility Control Model v1 — confirmation state machine + vertical slice.

Isolated prototype. No production branch, lease, or repository mutations.
"""
from __future__ import annotations

from typing import Any

from .intent import parse_intent, StructuredIntent
from .policy_mock import authorize
from .risk import classify_risk
from .scar_events import emit_decision


def _announce(intent: StructuredIntent, risk: str) -> str:
    return (
        f"Action: {intent.action}. "
        f"Target: {intent.target or 'n/a'}. "
        f"Scope: {intent.scope}. "
        f"Risk: {risk}. "
        f"Confirm?"
    )


def handle_command(
    command: str,
    *,
    pending: bool = False,
    lease_scope: str = "user_workspace",
    interface: str = "voice",
) -> dict[str, Any]:
    """
    Vertical slice:
      parse → risk → confirm if needed → authorize → mock execute → SCAR

    pending=True means the user already confirmed the prior destructive intent
    (same command text re-submitted after confirmation).
    """
    parsed = parse_intent(command)

    if parsed.get("status") == "CANCEL":
        scar = emit_decision(
            interface=interface,
            action=None,
            risk="n/a",
            result="cancelled",
            confirmation="cancelled",
        )
        return {
            "status": "CANCELLED",
            "executed": False,
            "scar": scar,
        }

    if parsed.get("status") == "CLARIFICATION_REQUIRED":
        scar = emit_decision(
            interface=interface,
            action=None,
            risk="unknown",
            result="clarification_required",
        )
        return {
            "status": "CLARIFICATION_REQUIRED",
            "message": parsed.get("message"),
            "executed": False,
            "scar": scar,
        }

    intent: StructuredIntent = parsed["intent"]
    risk_info = classify_risk(intent)
    risk = risk_info["risk"]
    need_confirm = risk_info["confirmation_required"]

    if need_confirm and not pending:
        scar = emit_decision(
            interface=interface,
            action=intent.action,
            risk=risk,
            result="pending_confirmation",
            confirmation="required",
        )
        return {
            "status": "CONFIRM_REQUIRED",
            "action": intent.action,
            "target": intent.target,
            "scope": intent.scope,
            "risk": risk,
            "announcement": _announce(intent, risk),
            "executed": False,
            "scar": scar,
        }

    auth = authorize(intent, lease_scope=lease_scope)
    if auth["status"] == "DENIED":
        scar = emit_decision(
            interface=interface,
            action=intent.action,
            risk=risk,
            result="denied",
            confirmation="accepted" if pending else None,
        )
        return {
            "status": "DENIED",
            "reason": auth["reason"],
            "executed": False,
            "scar": scar,
        }

    # Mock execution only — no filesystem or git side effects.
    scar = emit_decision(
        interface=interface,
        action=intent.action,
        risk=risk,
        result="executed",
        confirmation="accepted" if pending or not need_confirm else None,
    )
    return {
        "status": "EXECUTED",
        "action": intent.action,
        "target": intent.target,
        "executed": True,
        "scar": scar,
    }
