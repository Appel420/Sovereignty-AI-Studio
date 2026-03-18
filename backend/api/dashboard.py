"""
Sovereignty AI Studio — Security Dashboard API
Provides audit log and usage stats endpoints for the dashboard.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def get_audit_summary(
    *,
    user_id: Optional[str] = None,
    action_prefix: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    """Return recent audit log entries for the dashboard."""
    from analytics.audit_logger import get_audit_logs

    logs = get_audit_logs(
        user_id=user_id,
        action=action_prefix,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(logs),
        "logs": logs,
    }


def get_usage_stats(
    *,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Return token usage summary for the dashboard."""
    from analytics.usage_tracker import get_usage_summary

    summary = get_usage_summary(
        org_id=org_id,
        user_id=user_id,
        project_id=project_id,
        limit=limit,
    )
    total_tokens = sum(row.get("total_tokens") or 0 for row in summary)
    total_calls = sum(row.get("call_count") or 0 for row in summary)
    return {
        "total_tokens": total_tokens,
        "total_calls": total_calls,
        "by_provider": summary,
    }


def get_system_health() -> Dict[str, Any]:
    """Return sovereign bridge health status."""
    try:
        from ai_core.sovereign_bridge import SovereignBridge

        bridge = SovereignBridge()
        provider_health = bridge.health()
    except Exception as exc:  # noqa: BLE001
        provider_health = {"error": str(exc)}

    return {
        "sovereign_bridge": provider_health,
        "status": "sovereign",
    }
