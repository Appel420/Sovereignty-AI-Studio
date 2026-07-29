"""ProjectionEngine v1.0 regression tests."""
from __future__ import annotations

from backend.ecosystem.projection_engine import (
    DataScope,
    EcosystemMenuItem,
    MenuStatus,
    Projection,
    ProjectionCache,
    RequestContext,
    RuntimeHealth,
    derive_projection,
    project_menu,
    projection_cache_key,
    to_audit_projection,
)


ITEMS = (
    EcosystemMenuItem(
        id="streaming",
        label="Streaming",
        group="Life",
        kind="direct_link",
        status=MenuStatus.ACTIVE,
        data_scope=DataScope.USER_OWNED,
        requires=("identity_verified",),
        owner="external",
        external_redirect=True,
    ),
    EcosystemMenuItem(
        id="omega",
        label="Omega",
        group="Classified",
        kind="panel",
        status=MenuStatus.CONFIGURED,
        data_scope=DataScope.SYNTHETIC,
        requires=("builder.schema.inspect",),
        owner="system",
        schema_only=True,
    ),
    EcosystemMenuItem(
        id="private-memory",
        label="Private Memory",
        group="Security",
        kind="route",
        status=MenuStatus.ACTIVE,
        data_scope=DataScope.PRIVATE,
        requires=("memory.read",),
    ),
    EcosystemMenuItem(
        id="blocked",
        label="Blocked",
        group="Security",
        kind="tool",
        status=MenuStatus.DENY,
        data_scope=DataScope.NONE,
        requires=("identity_verified",),
    ),
)

HEALTH = {item.id: RuntimeHealth.OK for item in ITEMS}


def test_user_projection_hides_unassigned_and_schema_only_items() -> None:
    context = RequestContext(
        identity_id="user-1",
        grants=frozenset({"identity_verified"}),
        assignments=frozenset({"streaming"}),
    )
    result = project_menu(ITEMS, context, HEALTH, Projection.USER)
    visible = {item.id for item in result if item.visible}
    assert visible == {"streaming"}
    assert result[0].enabled is True


def test_builder_projection_is_synthetic_and_requires_builder_authority() -> None:
    context = RequestContext(
        identity_id="owner-1",
        roles=frozenset({"OWNER", "BUILDER"}),
        grants=frozenset({"builder.schema.inspect"}),
        builder_allowed=True,
    )
    result = project_menu(ITEMS, context, HEALTH, Projection.BUILDER)
    omega = next(item for item in result if item.id == "omega")
    assert omega.visible is True
    assert omega.enabled is True
    assert omega.data_mode == "synthetic"


def test_unauthorized_builder_cannot_elevate_with_request_parameter() -> None:
    context = RequestContext(identity_id="user-1")
    assert derive_projection(context) is Projection.USER
    result = project_menu(ITEMS, context, HEALTH, Projection.AUDIT)
    assert all(item.visible is False for item in result)


def test_audit_dto_contains_metadata_only() -> None:
    audit = to_audit_projection(ITEMS[2]).to_dict()
    assert audit["id"] == "private-memory"
    assert audit["data_mode"] == "none"
    assert "private_payload" not in audit
    assert "credentials" not in audit
    assert "secrets" not in audit
    assert "memory_payload" not in audit


def test_deny_and_unavailable_are_never_enabled() -> None:
    context = RequestContext(
        identity_id="user-1",
        grants=frozenset({"identity_verified"}),
        assignments=frozenset({"blocked"}),
    )
    result = project_menu(ITEMS, context, HEALTH, Projection.USER)
    blocked = next(item for item in result if item.id == "blocked")
    assert blocked.visible is True
    assert blocked.enabled is False


def test_projection_cache_isolated_by_identity_assignment_and_policy() -> None:
    base = RequestContext(identity_id="user-1", policy_version="p1")
    different_identity = RequestContext(identity_id="user-2", policy_version="p1")
    different_policy = RequestContext(identity_id="user-1", policy_version="p2")
    assert projection_cache_key(base, Projection.USER) != projection_cache_key(different_identity, Projection.USER)
    assert projection_cache_key(base, Projection.USER) != projection_cache_key(different_policy, Projection.USER)

    cache = ProjectionCache()
    value = project_menu(ITEMS, base, HEALTH, Projection.USER)
    cache.put(projection_cache_key(base, Projection.USER), value)
    assert cache.get(projection_cache_key(different_identity, Projection.USER)) is None
    assert len(cache) == 1


def test_projection_result_is_immutable_for_request_lifecycle() -> None:
    context = RequestContext(
        identity_id="user-1",
        grants=frozenset({"identity_verified"}),
        assignments=frozenset({"streaming"}),
    )
    result = project_menu(ITEMS, context, HEALTH)
    assert isinstance(result, tuple)
    assert result[0].data_scope is DataScope.USER_OWNED
