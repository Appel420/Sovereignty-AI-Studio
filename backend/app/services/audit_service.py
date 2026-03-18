"""
Audit service — log all critical system actions with immutable records.
"""
import json
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    action: str,
    actor_id: Optional[int] = None,
    actor_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
) -> AuditLog:
    """Persist an audit log entry. Fire-and-forget safe — swallows DB errors."""
    try:
        entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception:
        db.rollback()
        raise


def query_logs(
    db: Session,
    actor_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[AuditLog]:
    """Query audit logs with optional filters."""
    q = db.query(AuditLog)
    filters = []
    if actor_id is not None:
        filters.append(AuditLog.actor_id == actor_id)
    if action:
        filters.append(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if status:
        filters.append(AuditLog.status == status)
    if since:
        filters.append(AuditLog.created_at >= since)
    if until:
        filters.append(AuditLog.created_at <= until)
    if filters:
        q = q.filter(and_(*filters))
    return (
        q.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_logs(
    db: Session,
    actor_id: Optional[int] = None,
    action: Optional[str] = None,
    since: Optional[datetime] = None,
) -> int:
    q = db.query(AuditLog)
    if actor_id is not None:
        q = q.filter(AuditLog.actor_id == actor_id)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if since:
        q = q.filter(AuditLog.created_at >= since)
    return q.count()
