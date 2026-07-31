"""Regression tests for the explicit identity adapter boundary."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from ecosystem.identity_adapter import user_to_request_context


@dataclass
class User:
    id: int
    roles: tuple[str, ...] = ()
    grants: tuple[str, ...] = ()
    assignments: tuple[str, ...] = ()


def test_adapter_maps_explicit_user_state() -> None:
    context = user_to_request_context(
        User(id=7, roles=("BUILDER",), grants=("dashboard:build",), assignments=("dashboard-builder",)),
        manifest_version="1.0",
    )
    assert context.identity_id == "7"
    assert context.roles == frozenset({"BUILDER"})
    assert context.grants == frozenset({"dashboard:build"})
    assert context.assignments == frozenset({"dashboard-builder"})
    assert context.builder_allowed is True


def test_adapter_accepts_verified_external_claims_without_engine_knowledge() -> None:
    context = user_to_request_context(
        User(id=8),
        manifest_version="1.0",
        identity_roles=("AUDITOR",),
        identity_grants=("audit:read",),
        identity_assignments=(),
        policy_version="keycloak-policy-4",
        assignment_version="assignment-2",
    )
    assert context.roles == frozenset({"AUDITOR"})
    assert context.grants == frozenset({"audit:read"})
    assert context.policy_version == "keycloak-policy-4"
    assert context.assignment_version == "assignment-2"
    assert context.audit_allowed is True


def test_missing_identity_attributes_fail_closed() -> None:
    context = user_to_request_context(User(id=9), manifest_version="1.0")
    assert context.roles == frozenset()
    assert context.grants == frozenset()
    assert context.assignments == frozenset()
    assert context.builder_allowed is False
    assert context.audit_allowed is False


def test_missing_identity_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="must have an id"):
        user_to_request_context(object(), manifest_version="1.0")
