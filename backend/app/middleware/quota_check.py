"""
Quota Check Middleware
Intercepts AI requests and enforces token quotas.
Routes to local models if external quota exceeded.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.services.quota_service import QuotaManager, QuotaExceededError

logger = logging.getLogger(__name__)


class QuotaCheckMiddleware:
    """Middleware that checks token quotas before routing to providers."""

    def __init__(self, app, db: Session):
        self.app = app
        self.db = db
        self.quota_manager = QuotaManager(db)

    async def __call__(self, request: Request, call_next: Callable):
        """Process request, check quota, route accordingly."""
        # Only intercept AI request paths
        if not request.url.path.startswith("/api/ai"):
            return await call_next(request)

        # Extract user and provider from request
        try:
            body = await request.json()
        except Exception:
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        provider = body.get("provider", "openai")
        estimated_tokens = len(body.get("prompt", "").split()) * 1.3  # Rough estimate

        if not user_id:
            return await call_next(request)

        # Check quota for requested provider
        try:
            self.quota_manager.check_quota(
                user_id=user_id,
                provider=provider,
                requested_tokens=int(estimated_tokens),
            )
            logger.debug(f"Quota OK: user={user_id} provider={provider}")
            return await call_next(request)

        except QuotaExceededError as exc:
            logger.warning(f"Quota exceeded: {exc}")

            # Auto-fallback to local model
            fallback_provider = self.quota_manager.suggest_fallback_provider(
                user_id, provider
            )
            logger.info(
                f"Auto-routing user={user_id} from {provider} to {fallback_provider}"
            )

            # Update request to use local provider
            body["provider"] = fallback_provider
            request._body = None  # Clear cached body

            # Include quota warning in response
            response = await call_next(request)
            if isinstance(response, JSONResponse):
                response.headers["X-Quota-Warning"] = (
                    f"Quota exceeded for {provider}; routed to {fallback_provider}"
                )

            return response


def check_quota_for_provider(
    db: Session,
    user_id: int,
    provider: str,
    tokens: int,
) -> dict:
    """
    Standalone function to check quota and get status.
    Raises QuotaExceededError if limit exceeded.
    """
    quota_manager = QuotaManager(db)
    quota_manager.check_quota(user_id, provider, tokens)
    return quota_manager.get_available_quota(user_id, provider)


def get_quota_status(db: Session, user_id: int) -> dict:
    """Get complete quota status for user."""
    quota_manager = QuotaManager(db)
    return quota_manager.get_quota_report(user_id)
