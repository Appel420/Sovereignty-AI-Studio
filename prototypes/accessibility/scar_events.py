"""SCAR-style events for accessibility decisions — metadata only, no voice audio."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def emit_decision(
    *,
    interface: str = "voice",
    action: str | None,
    risk: str,
    result: str,
    confirmation: str | None = None,
) -> dict[str, Any]:
    return {
        "event_type": "ACTION_DECISION",
        "event_class": "policy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "interface": interface,
            "action": action,
            "risk": risk,
            "confirmation": confirmation,
            "result": result,
        },
    }
