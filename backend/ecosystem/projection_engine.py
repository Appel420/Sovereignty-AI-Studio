"""Server-side ecosystem menu projection and cache isolation.

The manifest is declarative. Visibility, enablement, data mode, and projection
are derived per authenticated request from identity, grants, assignments,
policy, and runtime health. This module is framework-agnostic so the canonical
FastAPI routes and the root SGHv119.html dashboard can share one contract.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import json
from threading import RLock
from typing import Iterable, Mapping


class Projection(StrEnum):
    USER = "user"
    BUILDER = "builder"
    AUDIT = "audit"


class MenuStatus(StrEnum):
    DECLARED = "DECLARED"
    CONFIGURED = "CONFIGURED"
    AVAILABLE = "AVAILABLE"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    UNAVAILABLE = "UNAVAILABLE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


class DataScope(StrEnum):
    PUBLIC = "public"
    USER_OWNED = "user-owned"
    PRIVATE = "private"
    EVIDENCE = "evidence"
    SYNTHETIC = "synthetic"
    NONE = "none"


class RuntimeHealth(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EcosystemMenuItem:
    """Declarative menu/catalog entry; never store request-specific visibility."""

    id: str
    label: str
    group: str
    kind: str
    status: MenuStatus
    data_scope: DataScope
    requires: tuple[str, ...] = ()
    owner: str = "studio"
    version: str = "1.0"
    route: str | None = None
    external_redirect: bool = False
    schema_only: bool = False
    provider: str | None = None
    policy_state: str = "UNREVIEWED"
    last_seen: str | None = None


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Immutable authorization inputs for one projection evaluation."""

    identity_id: str
    roles: frozenset[str] = frozenset()
    grants: frozenset[str] = frozenset()
    assignments: frozenset[str] = frozenset()
    policy_version: str = "unknown"
    manifest_version: str = "unknown"
    assignment_version: str = "unknown"
    builder_allowed: bool = False
    audit_allowed: bool = False


@dataclass(frozen=True, slots=True)
class ProjectedMenuItem:
    """Safe DTO sent to a renderer; data mode is always explicit."""

    id: str
    label: str
    group: str
    kind: str
    status: MenuStatus
    data_scope: DataScope
    route: str | None
    external_redirect: bool
    owner: str
    version: str
    schema_only: bool
    provider: str | None
    policy_state: str
    last_seen: str | None
    visible: bool
    enabled: bool
    runtime_health: RuntimeHealth
    data_mode: str
    reason: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "group": self.group,
            "kind": self.kind,
            "status": self.status.value,
            "data_scope": self.data_scope.value,
            "route": self.route,
            "external_redirect": self.external_redirect,
            "owner": self.owner,
            "version": self.version,
            "schema_only": self.schema_only,
            "provider": self.provider,
            "policy_state": self.policy_state,
            "last_seen": self.last_seen,
            "visible": self.visible,
            "enabled": self.enabled,
            "runtime_health": self.runtime_health.value,
            "data_mode": self.data_mode,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AuditProjectionItem:
    """Metadata-only audit DTO. No payload, credential, memory, or user data."""

    id: str
    label: str
    group: str
    kind: str
    provider: str | None
    status: MenuStatus
    policy_state: str
    data_scope: DataScope
    owner: str
    version: str
    schema_only: bool
    last_seen: str | None
    runtime_health: RuntimeHealth

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "group": self.group,
            "kind": self.kind,
            "provider": self.provider,
            "status": self.status.value,
            "policy_state": self.policy_state,
            "data_scope": self.data_scope.value,
            "owner": self.owner,
            "version": self.version,
            "schema_only": self.schema_only,
            "last_seen": self.last_seen,
            "runtime_health": self.runtime_health.value,
            "data_mode": DataScope.NONE.value,
        }


def derive_projection(context: RequestContext) -> Projection:
    """Derive the strongest permitted view; request parameters cannot elevate it."""
    if context.audit_allowed and ("AUDITOR" in context.roles or "OWNER" in context.roles):
        return Projection.AUDIT
    if context.builder_allowed and ("BUILDER" in context.roles or "OWNER" in context.roles):
        return Projection.BUILDER
    return Projection.USER


def _authorized(item: EcosystemMenuItem, context: RequestContext) -> bool:
    return all(requirement in context.grants for requirement in item.requires)


def _data_mode(item: EcosystemMenuItem, projection: Projection) -> str:
    if projection is Projection.AUDIT:
        return DataScope.NONE.value
    if projection is Projection.BUILDER:
        return DataScope.SYNTHETIC.value
    if item.data_scope is DataScope.PRIVATE:
        return "redacted"
    return "live"


def project_menu(
    items: Iterable[EcosystemMenuItem],
    context: RequestContext,
    health: Mapping[str, RuntimeHealth | str],
    projection: Projection | None = None,
) -> tuple[ProjectedMenuItem, ...]:
    """Create an immutable request-scoped projection of the declarative catalog."""
    selected = projection or derive_projection(context)
    if selected is Projection.AUDIT and not context.audit_allowed:
        selected = Projection.USER
    if selected is Projection.BUILDER and not context.builder_allowed:
        selected = Projection.USER

    projected: list[ProjectedMenuItem] = []
    for item in items:
        authorized = _authorized(item, context)
        assigned = item.id in context.assignments
        runtime = RuntimeHealth(health.get(item.id, RuntimeHealth.UNKNOWN))
        visible = (
            selected is Projection.AUDIT
            or (selected is Projection.BUILDER and context.builder_allowed and (authorized or item.schema_only))
            or (selected is Projection.USER and assigned and authorized)
        )
        blocked_status = item.status in {MenuStatus.DENY, MenuStatus.UNAVAILABLE}
        enabled = visible and authorized and not blocked_status and runtime is RuntimeHealth.OK
        reason = None
        if not visible:
            reason = "not_in_current_projection"
        elif not authorized:
            reason = "missing_required_grant"
        elif blocked_status:
            reason = f"item_status_{item.status.value.lower()}"
        elif runtime is not RuntimeHealth.OK:
            reason = "runtime_unhealthy"

        projected.append(
            ProjectedMenuItem(
                id=item.id,
                label=item.label,
                group=item.group,
                kind=item.kind,
                status=item.status,
                data_scope=item.data_scope,
                route=item.route,
                external_redirect=item.external_redirect,
                owner=item.owner,
                version=item.version,
                schema_only=item.schema_only,
                provider=item.provider,
                policy_state=item.policy_state,
                last_seen=item.last_seen,
                visible=visible,
                enabled=enabled,
                runtime_health=runtime,
                data_mode=_data_mode(item, selected),
                reason=reason,
            )
        )
    return tuple(projected)


def to_audit_projection(item: EcosystemMenuItem | ProjectedMenuItem) -> AuditProjectionItem:
    """Convert catalog/projection data to a metadata-only audit DTO."""
    return AuditProjectionItem(
        id=item.id,
        label=item.label,
        group=item.group,
        kind=item.kind,
        provider=item.provider,
        status=item.status,
        policy_state=item.policy_state,
        data_scope=item.data_scope,
        owner=item.owner,
        version=item.version,
        schema_only=item.schema_only,
        last_seen=item.last_seen,
        runtime_health=getattr(item, "runtime_health", RuntimeHealth.UNKNOWN),
    )


def projection_cache_key(context: RequestContext, projection: Projection) -> str:
    """Build an identity/policy/manifest scoped cache key."""
    return json.dumps(
        {
            "identity_id": context.identity_id,
            "roles": sorted(context.roles),
            "grants": sorted(context.grants),
            "assignments": sorted(context.assignments),
            "policy_version": context.policy_version,
            "manifest_version": context.manifest_version,
            "assignment_version": context.assignment_version,
            "projection": projection.value,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class ProjectionCache:
    """Small process-local cache with complete identity and policy isolation."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[ProjectedMenuItem, ...]] = {}
        self._lock = RLock()

    def get(self, key: str) -> tuple[ProjectedMenuItem, ...] | None:
        with self._lock:
            return self._entries.get(key)

    def put(self, key: str, value: tuple[ProjectedMenuItem, ...]) -> None:
        with self._lock:
            self._entries[key] = value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
