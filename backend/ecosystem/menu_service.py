"""Service adapter between FastAPI sessions and ProjectionEngine."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .manifest import ECOSYSTEM_MANIFEST_VERSION, ECOSYSTEM_MENU
from .projection_engine import (
    Projection,
    ProjectionCache,
    ProjectedMenuItem,
    RequestContext,
    RuntimeHealth,
    derive_projection,
    project_menu,
    projection_cache_key,
    to_audit_projection,
)

_CACHE = ProjectionCache()


def _string_set(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset({value})
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(item) for item in value)
    return frozenset()


def _user_value(user: Any, name: str) -> Any:
    """Read only explicit session/user attributes; never synthesize authority."""
    return getattr(user, name, None)


def build_request_context(user: Any) -> RequestContext:
    """Build context from existing authenticated state without privilege fallback."""
    user_id = _user_value(user, "id")
    if user_id is None:
        raise ValueError("authenticated user must have an id")

    roles = _string_set(_user_value(user, "roles"))
    grants = _string_set(_user_value(user, "grants"))
    assignments = _string_set(_user_value(user, "assignments"))
    return RequestContext(
        identity_id=str(user_id),
        roles=roles,
        grants=grants,
        assignments=assignments,
        policy_version=str(_user_value(user, "policy_version") or "unknown"),
        manifest_version=ECOSYSTEM_MANIFEST_VERSION,
        assignment_version=str(_user_value(user, "assignment_version") or "unknown"),
        builder_allowed="dashboard:build" in grants,
        audit_allowed="audit:read" in grants,
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
    # requested_projection is deliberately ignored as an authority input.
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
