"""Regression tests for the authenticated ecosystem menu adapter."""
from __future__ import annotations

from dataclasses import dataclass

from ecosystem.menu_service import build_request_context, get_menu_projection


@dataclass
class User:
    id: int
    roles: tuple[str, ...] = ()
    grants: tuple[str, ...] = ()
    assignments: tuple[str, ...] = ()


def test_user_projection_uses_existing_session_state_only() -> None:
    user = User(
        id=7,
        grants=("identity_verified",),
        assignments=("streaming",),
    )
    result = get_menu_projection(user)
    assert result["projection"] == "user"
    assert [item["id"] for item in result["items"]] == ["streaming"]


def test_client_projection_parameter_cannot_elevate_user() -> None:
    user = User(id=7)
    result = get_menu_projection(user, requested_projection="audit")
    assert result["projection"] == "user"
    assert result["items"] == []


def test_builder_projection_is_authorized_by_grant_not_role_name_alone() -> None:
    user = User(
        id=1,
        roles=("BUILDER",),
        grants=("dashboard:build", "role:schema.inspect"),
    )
    context = build_request_context(user)
    assert context.builder_allowed is True
    result = get_menu_projection(user, requested_projection="builder")
    assert result["projection"] == "builder"
    ids = {item["id"] for item in result["items"]}
    assert "dashboard-builder" in ids
    assert "role-catalog" in ids
    assert all(item["data_mode"] == "synthetic" for item in result["items"])


def test_audit_projection_requires_audit_grant() -> None:
    user = User(id=1, roles=("AUDITOR",), grants=("audit:read",))
    result = get_menu_projection(user, requested_projection="audit")
    assert result["projection"] == "audit"
    assert result["items"]
    for item in result["items"]:
        assert item["data_mode"] == "none"
        assert "credentials" not in item
        assert "private_payload" not in item
