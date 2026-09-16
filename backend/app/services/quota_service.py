"""
Token Quota Management Service
Enforces per-user, per-org, per-project token limits.
Prioritizes local models to prevent external API overages.
"""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

logger = logging.getLogger(__name__)


@dataclass
class QuotaLimit:
    """Token quota configuration."""
    daily_limit: int
    monthly_limit: int
    burst_limit: int  # per-request max
    provider: str
    priority_local: bool = True


class QuotaExceededError(Exception):
    """Raised when token quota is exceeded."""
    pass


class QuotaManager:
    """Manages token usage quotas with local-first routing."""

    # Default quotas (per user)
    DEFAULT_DAILY_QUOTA = 100_000
    DEFAULT_MONTHLY_QUOTA = 2_000_000
    DEFAULT_BURST_QUOTA = 50_000

    # Local models have NO limits (infinite quota)
    LOCAL_MODELS = {
        "local_gguf",
        "local_ollama",
        "local_llama",
        "sovereign_bridge_local",
    }

    # Premium models (OpenAI, Anthropic) have strict limits
    PREMIUM_MODELS = {
        "openai": QuotaLimit(
            daily_limit=100_000,
            monthly_limit=2_000_000,
            burst_limit=50_000,
            provider="openai",
        ),
        "anthropic": QuotaLimit(
            daily_limit=80_000,
            monthly_limit=1_500_000,
            burst_limit=40_000,
            provider="anthropic",
        ),
        "xai": QuotaLimit(
            daily_limit=120_000,
            monthly_limit=2_500_000,
            burst_limit=60_000,
            provider="xai",
        ),
    }

    def __init__(self, db: Session):
        """Initialize quota manager with database session."""
        self.db = db

    def get_usage_today(self, user_id: int, provider: Optional[str] = None) -> int:
        """Get token usage for today (UTC)."""
        from app.models.usage import UsageRecord

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        query = self.db.query(sqlfunc.sum(UsageRecord.total_tokens)).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= today_start,
        )

        if provider:
            query = query.filter(UsageRecord.provider == provider)

        result = query.scalar()
        return result or 0

    def get_usage_this_month(self, user_id: int, provider: Optional[str] = None) -> int:
        """Get token usage for this month (UTC)."""
        from app.models.usage import UsageRecord

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        query = self.db.query(sqlfunc.sum(UsageRecord.total_tokens)).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= month_start,
        )

        if provider:
            query = query.filter(UsageRecord.provider == provider)

        result = query.scalar()
        return result or 0

    def check_quota(
        self,
        user_id: int,
        provider: str,
        requested_tokens: int,
    ) -> bool:
        """
        Check if request would exceed quota.
        Returns True if allowed, raises QuotaExceededError if not.
        """
        # Local models have infinite quota
        if provider in self.LOCAL_MODELS:
            logger.debug(
                f"Local provider '{provider}' — quota unlimited",
            )
            return True

        # Get quota limits for provider
        quota = self.PREMIUM_MODELS.get(provider)
        if not quota:
            logger.warning(f"Unknown provider '{provider}' — default strict limits")
            quota = self.PREMIUM_MODELS["openai"]

        # Check burst limit (single request)
        if requested_tokens > quota.burst_limit:
            raise QuotaExceededError(
                f"Request exceeds burst limit of {quota.burst_limit:,} tokens "
                f"(requested: {requested_tokens:,})"
            )

        # Check daily limit
        daily_usage = self.get_usage_today(user_id, provider)
        if daily_usage + requested_tokens > quota.daily_limit:
            remaining = quota.daily_limit - daily_usage
            raise QuotaExceededError(
                f"Daily quota exceeded for {provider}. "
                f"Limit: {quota.daily_limit:,}, Used: {daily_usage:,}, "
                f"Requested: {requested_tokens:,}, Remaining: {remaining:,}"
            )

        # Check monthly limit
        monthly_usage = self.get_usage_this_month(user_id, provider)
        if monthly_usage + requested_tokens > quota.monthly_limit:
            remaining = quota.monthly_limit - monthly_usage
            raise QuotaExceededError(
                f"Monthly quota exceeded for {provider}. "
                f"Limit: {quota.monthly_limit:,}, Used: {monthly_usage:,}, "
                f"Requested: {requested_tokens:,}, Remaining: {remaining:,}"
            )

        logger.debug(
            f"Quota check passed: {provider} user={user_id} "
            f"daily={daily_usage}/{quota.daily_limit} "
            f"monthly={monthly_usage}/{quota.monthly_limit}"
        )
        return True

    def get_available_quota(self, user_id: int, provider: str) -> dict:
        """Return remaining quota for provider."""
        if provider in self.LOCAL_MODELS:
            return {
                "provider": provider,
                "type": "local",
                "daily_remaining": float("inf"),
                "monthly_remaining": float("inf"),
                "status": "unlimited",
            }

        quota = self.PREMIUM_MODELS.get(provider, self.PREMIUM_MODELS["openai"])
        daily_used = self.get_usage_today(user_id, provider)
        monthly_used = self.get_usage_this_month(user_id, provider)

        daily_remaining = max(0, quota.daily_limit - daily_used)
        monthly_remaining = max(0, quota.monthly_limit - monthly_used)

        return {
            "provider": provider,
            "type": "premium",
            "daily_limit": quota.daily_limit,
            "daily_used": daily_used,
            "daily_remaining": daily_remaining,
            "daily_percent": (daily_used / quota.daily_limit * 100) if quota.daily_limit > 0 else 0,
            "monthly_limit": quota.monthly_limit,
            "monthly_used": monthly_used,
            "monthly_remaining": monthly_remaining,
            "monthly_percent": (monthly_used / quota.monthly_limit * 100) if quota.monthly_limit > 0 else 0,
            "burst_limit": quota.burst_limit,
            "status": "normal"
            if daily_remaining > 0 and monthly_remaining > 0
            else "warning"
            if daily_remaining > quota.daily_limit * 0.2
            else "critical",
        }

    def suggest_fallback_provider(self, user_id: int, original_provider: str) -> str:
        """
        If quota exceeded, suggest local provider instead.
        Returns "local_gguf" or similar.
        """
        logger.warning(
            f"Quota exceeded for {original_provider} — fallback to local model"
        )
        return "local_gguf"

    def get_quota_report(self, user_id: int) -> dict:
        """Generate quota usage report for all providers."""
        report = {
            "user_id": user_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "providers": {},
        }

        # Check all premium providers
        for provider_name in self.PREMIUM_MODELS.keys():
            report["providers"][provider_name] = self.get_available_quota(
                user_id, provider_name
            )

        # Add local provider info
        report["providers"]["local"] = {
            "provider": "local",
            "type": "local",
            "status": "unlimited",
            "models": list(self.LOCAL_MODELS),
        }

        return report
