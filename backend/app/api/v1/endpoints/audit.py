"""
Audit log API endpoints — filterable audit log viewer for security dashboard.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.dependencies import get_database, get_current_active_user
from app.models.user import User
from app.services.audit_service import query_logs, count_logs

router = APIRouter()


@router.get("/logs")
async def get_audit_logs(
    actor_id: Optional[int] = Query(None, description="Filter by actor user ID"),
    action: Optional[str] = Query(None, description="Filter by action (partial match)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    status: Optional[str] = Query(None, description="Filter by status: success|failure"),
    since: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    until: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve audit logs with optional filters.
    Returns paginated results ordered by most recent first.
    """
    logs = query_logs(
        db,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        status=status,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    total = count_logs(db, actor_id=actor_id, action=action, since=since)

    return {
        "items": [
            {
                "id": log.id,
                "actor_id": log.actor_id,
                "actor_email": log.actor_email,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/logs/actions")
async def list_action_types(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """Return distinct action types present in the audit log."""
    from app.models.audit_log import AuditLog
    rows = db.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    return {"actions": [r[0] for r in rows]}
