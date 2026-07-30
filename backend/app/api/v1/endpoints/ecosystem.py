"""Authenticated ecosystem menu projection endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_active_user
from app.models.user import User
from ecosystem.menu_service import get_menu_projection

router = APIRouter()


@router.get("/menu")
async def ecosystem_menu(
    requested_projection: str | None = Query(default=None, alias="projection"),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    """Return the menu derived from the authenticated session.

    The query parameter is accepted for compatibility/diagnostics only. It is
    never used to elevate a user to builder or audit projection.
    """
    return get_menu_projection(current_user, requested_projection)
