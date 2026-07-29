"""Declarative ecosystem menu manifest for the canonical Studio runtime."""
from __future__ import annotations

from .projection_engine import DataScope, EcosystemMenuItem, MenuStatus


ECOSYSTEM_MANIFEST_VERSION = "1.0"


ECOSYSTEM_MENU: tuple[EcosystemMenuItem, ...] = (
    EcosystemMenuItem(
        id="dashboard",
        label="Dashboard",
        group="Core",
        kind="panel",
        status=MenuStatus.ACTIVE,
        data_scope=DataScope.USER_OWNED,
        policy_state="OWNER_POLICY",
    ),
    EcosystemMenuItem(
        id="audit-trail",
        label="Audit Trail",
        group="Core",
        kind="route",
        route="/api/v1/audit/logs",
        status=MenuStatus.CONFIGURED,
        data_scope=DataScope.EVIDENCE,
        requires=("audit:read",),
        policy_state="RBAC",
    ),
    EcosystemMenuItem(
        id="ai-chat",
        label="AI Chat",
        group="AI & Agents",
        kind="route",
        route="/api/v1/studio",
        status=MenuStatus.CONFIGURED,
        data_scope=DataScope.USER_OWNED,
        requires=("ai:query",),
        policy_state="RBAC",
    ),
    EcosystemMenuItem(
        id="food-grocery",
        label="Food & Grocery",
        group="Life",
        kind="direct_link",
        status=MenuStatus.DECLARED,
        data_scope=DataScope.USER_OWNED,
        requires=("identity_verified",),
        owner="external",
        external_redirect=True,
        policy_state="DIRECT_LINK",
    ),
    EcosystemMenuItem(
        id="streaming",
        label="Streaming",
        group="Life",
        kind="direct_link",
        status=MenuStatus.DECLARED,
        data_scope=DataScope.USER_OWNED,
        requires=("identity_verified",),
        owner="external",
        external_redirect=True,
        policy_state="DIRECT_LINK",
    ),
    EcosystemMenuItem(
        id="device-center",
        label="Device Center",
        group="Device",
        kind="route",
        status=MenuStatus.CONFIGURED,
        data_scope=DataScope.PRIVATE,
        requires=("device:read",),
        policy_state="DEVICE_POLICY",
    ),
    EcosystemMenuItem(
        id="dashboard-builder",
        label="Dashboard Builder",
        group="Admin",
        kind="route",
        status=MenuStatus.CONFIGURED,
        data_scope=DataScope.SYNTHETIC,
        requires=("dashboard:build",),
        schema_only=True,
        policy_state="OWNER_APPROVAL",
    ),
    EcosystemMenuItem(
        id="role-catalog",
        label="Role Catalog",
        group="Admin",
        kind="route",
        status=MenuStatus.CONFIGURED,
        data_scope=DataScope.NONE,
        requires=("role:schema.inspect",),
        schema_only=True,
        policy_state="OWNER_APPROVAL",
    ),
)
