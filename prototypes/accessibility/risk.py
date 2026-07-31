"""Accessibility Control Model v1 — risk classification (prototype)."""
from __future__ import annotations

from .intent import StructuredIntent

# Actions that always require explicit confirmation in this prototype.
DESTRUCTIVE = frozenset({"delete_file", "deploy", "purge", "reset_credentials"})
HIGH = frozenset({"merge_main", "change_branch_protection"})


def classify_risk(intent: StructuredIntent | None) -> dict:
    if intent is None:
        return {
            "risk": "unknown",
            "confirmation_required": True,
        }

    if intent.action in DESTRUCTIVE or intent.scope == "production":
        return {
            "risk": "destructive",
            "confirmation_required": True,
        }

    if intent.action in HIGH:
        return {
            "risk": "high",
            "confirmation_required": True,
        }

    return {
        "risk": "low",
        "confirmation_required": False,
    }
