"""Service adapter between authenticated identities and ProjectionEngine."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .identity_adapter import user_to_request_context
from .manifest import ECOSYSTEM_MANIFEST_VERSION, ECOSYSTEM_MENU
from .projection_engine import (
    Projection,
    ProjectionCache,
    ProjectedMenuItem,
    RuntimeHealth,
    derive_projection,
    project_menu,
    projection_cache_key,
    to_audit_projection,
)

_CACHE = ProjectionCache()


def build_request_context(user: Any):
    """Build context through the explicit identity adapter boundary."""
    return user_to_request_context(
        user,
        manifest_version=ECOSYSTEM_MANIFEST_VERSION,
    )


def runtime_health() -> Mapping[str, RuntimeHealth]:
    """Return only verified local health facts; unknown is the safe default."""
    return {item.id: RuntimeHealth.UNKNOWN for item in ECOSYSTEM_MENU}


def _serialize_items(
    items: tuple[ProjectedMenuItem, ...], projection: Projection
) -> list[dict[str, object]]:
    if projection is Projection.AUDIT:
        return [to_audit_projection(item).to_dict() for item in items]
    return [item.to_dict() for item in items if item.visible]


def get_menu_projection(
    user: Any,
    requested_projection: str | None = None,
) -> dict[str, object]:
    """Return the session-derived menu projection; request input cannot elevate it."""
    context = build_request_context(user)
    projection = derive_projection(context)
    del requested_projection
    key = projection_cache_key(context, projection)
    projected = _CACHE.get(key)
    if projected is None:
        projected = project_menu(ECOSYSTEM_MENU, context, runtime_health(), projection)
        _CACHE.put(key, projected)

    return {
        "projection": projection.value,
        "identity_id": context.identity_id,
        "manifest_version": ECOSYSTEM_MANIFEST_VERSION,
        "items": _serialize_items(projected, projection),
    }


def clear_menu_cache() -> None:
    """Clear local projections after policy, assignment, or manifest changes."""
    _CACHE.clear()
