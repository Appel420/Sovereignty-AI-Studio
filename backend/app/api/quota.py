"""
Quota Management API Endpoints
Provides quota status, remaining balance, and usage reports.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.quota_check import get_quota_status, check_quota_for_provider
from app.services.quota_service import QuotaExceededError

router = APIRouter(prefix="/api/quota", tags=["quota"])


@router.get("/status")
async def get_quota_status_endpoint(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    GET /api/quota/status
    Return quota usage and remaining balance for all providers.
    """
    try:
        status = get_quota_status(db, current_user.id)
        return {
            "status": "ok",
            "data": status,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status/{provider}")
async def get_provider_quota(
    provider: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    GET /api/quota/status/{provider}
    Return quota status for specific provider.
    """
    from app.services.quota_service import QuotaManager

    quota_manager = QuotaManager(db)
    status = quota_manager.get_available_quota(current_user.id, provider)
    return {
        "status": "ok",
        "data": status,
    }


@router.post("/check")
async def check_quota_endpoint(
    request: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    POST /api/quota/check
    Check if request would exceed quota.
    Body: {"provider": "openai", "tokens": 5000}
    """
    try:
        provider = request.get("provider", "openai")
        tokens = request.get("tokens", 0)

        check_quota_for_provider(db, current_user.id, provider, tokens)

        return {
            "status": "ok",
            "allowed": True,
            "message": f"Request allowed for {provider}",
        }

    except QuotaExceededError as exc:
        return {
            "status": "quota_exceeded",
            "allowed": False,
            "message": str(exc),
            "fallback_provider": "local_gguf",
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/usage/today")
async def get_today_usage(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    GET /api/quota/usage/today
    Return token usage for today.
    """
    from app.services.quota_service import QuotaManager

    quota_manager = QuotaManager(db)
    usage = quota_manager.get_usage_today(current_user.id)

    return {
        "status": "ok",
        "period": "today",
        "tokens_used": usage,
    }


@router.get("/usage/this-month")
async def get_month_usage(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    GET /api/quota/usage/this-month
    Return token usage for this month.
    """
    from app.services.quota_service import QuotaManager

    quota_manager = QuotaManager(db)
    usage = quota_manager.get_usage_this_month(current_user.id)

    return {
        "status": "ok",
        "period": "this_month",
        "tokens_used": usage,
    }


@router.get("/models/local")
async def get_local_models(db: Session = Depends(get_db)):
    """
    GET /api/quota/models/local
    List all local models (unlimited quota).
    """
    from app.services.quota_service import QuotaManager

    return {
        "status": "ok",
        "type": "local",
        "models": list(QuotaManager.LOCAL_MODELS),
        "quota": "unlimited",
        "description": "Run locally on device — no token charges, no external API calls",
    }


@router.get("/models/premium")
async def get_premium_models(db: Session = Depends(get_db)):
    """
    GET /api/quota/models/premium
    List all premium (external) models with quota limits.
    """
    from app.services.quota_service import QuotaManager

    models = []
    for provider, quota in QuotaManager.PREMIUM_MODELS.items():
        models.append(
            {
                "provider": provider,
                "daily_limit": quota.daily_limit,
                "monthly_limit": quota.monthly_limit,
                "burst_limit": quota.burst_limit,
            }
        )

    return {
        "status": "ok",
        "type": "premium",
        "models": models,
    }
