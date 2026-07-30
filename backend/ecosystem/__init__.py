"""Canonical ecosystem backend contracts."""

from .projection_engine import (
    AuditProjectionItem,
    DataScope,
    EcosystemMenuItem,
    MenuStatus,
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

__all__ = [
    "AuditProjectionItem",
    "DataScope",
    "EcosystemMenuItem",
    "MenuStatus",
    "Projection",
    "ProjectionCache",
    "ProjectedMenuItem",
    "RequestContext",
    "RuntimeHealth",
    "derive_projection",
    "project_menu",
    "projection_cache_key",
    "to_audit_projection",
]
