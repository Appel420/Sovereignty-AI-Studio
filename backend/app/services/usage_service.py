"""
Usage tracking service — records AI token consumption per user/org/provider.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from datetime import datetime, timedelta

from app.models.usage import UsageRecord


def record_usage(
    db: Session,
    user_id: int,
    provider: str,
    model: str,
    action: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: Optional[float] = None,
    cost_usd: float = 0.0,
    status: str = "success",
    error_message: Optional[str] = None,
    org_id: Optional[int] = None,
) -> UsageRecord:
    """Persist a usage record after an AI call."""
    record = UsageRecord(
        user_id=user_id,
        org_id=org_id,
        provider=provider,
        model=model,
        action=action,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        status=status,
        error_message=error_message,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_user_usage_summary(
    db: Session,
    user_id: int,
    days: int = 30,
) -> dict:
    """Return aggregated usage stats for a user over the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            UsageRecord.provider,
            sqlfunc.sum(UsageRecord.total_tokens).label("tokens"),
            sqlfunc.sum(UsageRecord.cost_usd).label("cost"),
            sqlfunc.count(UsageRecord.id).label("calls"),
        )
        .filter(UsageRecord.user_id == user_id, UsageRecord.created_at >= since)
        .group_by(UsageRecord.provider)
        .all()
    )
    total_tokens = sum(r.tokens or 0 for r in rows)
    total_cost = sum(r.cost or 0.0 for r in rows)
    by_provider = {
        r.provider: {
            "tokens": r.tokens or 0,
            "cost_usd": round(r.cost or 0.0, 6),
            "calls": r.calls,
        }
        for r in rows
    }
    return {
        "user_id": user_id,
        "period_days": days,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "by_provider": by_provider,
    }


def get_recent_usage(
    db: Session,
    user_id: int,
    limit: int = 50,
) -> List[UsageRecord]:
    return (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user_id)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def get_org_usage_summary(
    db: Session,
    org_id: int,
    days: int = 30,
) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            UsageRecord.provider,
            sqlfunc.sum(UsageRecord.total_tokens).label("tokens"),
            sqlfunc.sum(UsageRecord.cost_usd).label("cost"),
            sqlfunc.count(UsageRecord.id).label("calls"),
        )
        .filter(UsageRecord.org_id == org_id, UsageRecord.created_at >= since)
        .group_by(UsageRecord.provider)
        .all()
    )
    return {
        "org_id": org_id,
        "period_days": days,
        "total_tokens": sum(r.tokens or 0 for r in rows),
        "total_cost_usd": round(sum(r.cost or 0.0 for r in rows), 6),
        "by_provider": {
            r.provider: {
                "tokens": r.tokens or 0,
                "cost_usd": round(r.cost or 0.0, 6),
                "calls": r.calls,
            }
            for r in rows
        },
    }
