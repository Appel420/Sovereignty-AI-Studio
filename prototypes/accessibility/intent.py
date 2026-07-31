"""Accessibility Control Model v1 — intent extraction (prototype).

Parses short commands into structured intents. Ambiguous input returns
CLARIFICATION_REQUIRED. Does not execute or authorize.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StructuredIntent:
    action: str
    target: str | None
    scope: str
    raw: str


def parse_intent(command: str) -> dict[str, Any]:
    text = (command or "").strip()
    if not text:
        return {
            "status": "CLARIFICATION_REQUIRED",
            "message": "Please repeat the command.",
            "intent": None,
        }

    lower = text.lower()

    if lower in {"cancel", "stop", "abort"}:
        return {"status": "CANCEL", "intent": None, "raw": text}

    # Destructive patterns → structured action (not keyword risk alone downstream)
    if lower.startswith("delete ") or lower.startswith("remove "):
        parts = text.split(maxsplit=1)
        target = parts[1].strip() if len(parts) > 1 else None
        if not target or target in {"the thing", "it", "that"}:
            return {
                "status": "CLARIFICATION_REQUIRED",
                "message": "What should be deleted? Name the file or target.",
                "intent": None,
            }
        return {
            "status": "PARSED",
            "intent": StructuredIntent(
                action="delete_file",
                target=target,
                scope="user_workspace",
                raw=text,
            ),
        }

    if lower.startswith("deploy "):
        parts = text.split(maxsplit=1)
        target = parts[1].strip() if len(parts) > 1 else "production"
        return {
            "status": "PARSED",
            "intent": StructuredIntent(
                action="deploy",
                target=target,
                scope="production",
                raw=text,
            ),
        }

    if lower.startswith("open ") or lower.startswith("show "):
        parts = text.split(maxsplit=1)
        target = parts[1].strip() if len(parts) > 1 else None
        return {
            "status": "PARSED",
            "intent": StructuredIntent(
                action="open",
                target=target,
                scope="user_workspace",
                raw=text,
            ),
        }

    # Ambiguous / unknown
    if any(w in lower for w in ("the thing", "stuff", "it")) and len(text.split()) < 5:
        return {
            "status": "CLARIFICATION_REQUIRED",
            "message": "Please name the exact action and target.",
            "intent": None,
        }

    return {
        "status": "CLARIFICATION_REQUIRED",
        "message": "Could not parse a known action. Try: open …, delete …, or cancel.",
        "intent": None,
    }
