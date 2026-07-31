"""Mock policy / capability / lease checks — isolated prototype only."""
from __future__ import annotations

from .intent import StructuredIntent


def authorize(intent: StructuredIntent, lease_scope: str = "user_workspace") -> dict:
    """Return ALLOW or DENY. No real registry or lease store."""
    if intent.scope == "production" and lease_scope != "production":
        return {
            "status": "DENIED",
            "reason": "LEASE_SCOPE_MISMATCH",
        }
    if intent.action == "deploy" and lease_scope == "development-only":
        return {
            "status": "DENIED",
            "reason": "LEASE_SCOPE_MISMATCH",
        }
    return {"status": "ALLOWED", "reason": None}
