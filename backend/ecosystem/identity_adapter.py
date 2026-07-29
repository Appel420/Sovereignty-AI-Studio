"""Explicit identity-to-projection context adapter.

This is the only application-facing translation boundary. ProjectionEngine does
not inspect SQLAlchemy models, JWT claims, Keycloak claims, or hardware identity
sources directly. Missing attributes remain empty and never grant authority.
"""
from __future__ import annotations

from typing import Any

from .projection_engine import RequestContext


def _string_set(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset({value})
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(item) for item in value)
    return frozenset()


def user_to_request_context(
    user: Any,
    *,
    manifest_version: str,
    identity_roles: Any = None,
    identity_grants: Any = None,
    identity_assignments: Any = None,
    policy_version: str | None = None,
    assignment_version: str | None = None,
) -> RequestContext:
    """Translate authenticated identity state without inventing permissions.

    Explicit adapter inputs take precedence so a future Keycloak/Gate/local
    identity provider can pass verified claims without changing the engine.
    In their absence, only explicitly present user attributes are read.
    """
    identity_id = getattr(user, "id", None)
    if identity_id is None:
        raise ValueError("authenticated identity must have an id")

    roles = _string_set(identity_roles if identity_roles is not None else getattr(user, "roles", None))
    grants = _string_set(identity_grants if identity_grants is not None else getattr(user, "grants", None))
    assignments = _string_set(
        identity_assignments
        if identity_assignments is not None
        else getattr(user, "assignments", None)
    )
    resolved_policy_version = policy_version or getattr(user, "policy_version", None) or "unknown"
    resolved_assignment_version = (
        assignment_version or getattr(user, "assignment_version", None) or "unknown"
    )

    return RequestContext(
        identity_id=str(identity_id),
        roles=roles,
        grants=grants,
        assignments=assignments,
        policy_version=str(resolved_policy_version),
        manifest_version=manifest_version,
        assignment_version=str(resolved_assignment_version),
        builder_allowed="dashboard:build" in grants,
        audit_allowed="audit:read" in grants,
    )
