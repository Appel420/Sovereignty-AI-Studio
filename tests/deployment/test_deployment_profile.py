from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.deployment.deployment_profile import (
    ValidationError,
    generate_fresh_profile,
    run_validation_pipeline,
    validate_profile,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "docs" / "schemas" / "deployment-profile" / "v1.json"


def profile():
    return generate_fresh_profile(
        owner_ref="local-owner-001",
        profile_type="personal",
        production_branch="production",
        integration_branch="integration",
        base_vault_dir="/tmp/sovereignty-test",
    )


def test_fresh_profile_validates_without_activation():
    p = profile()
    assert validate_profile(p, SCHEMA) == []
    report = run_validation_pipeline(p, SCHEMA)
    assert report.valid is True
    assert report.owner_approval_required is True
    assert "owner_approval_required" in report.steps_completed


def test_no_personal_topology_defaults_are_injected():
    p = profile()
    assert p.topology.production_branch == "production"
    assert p.topology.integration_branch == "integration"
    assert p.topology.development_lanes == []
    assert p.topology.agents == []
    assert p.topology.providers == []


def test_reference_only_profile_cannot_validate_for_activation():
    p = generate_fresh_profile(
        owner_ref="local-owner-001",
        profile_type="personal",
        production_branch="production",
        integration_branch="integration",
        base_vault_dir="/tmp/sovereignty-test",
        reference_only=True,
    )
    errors = validate_profile(p, SCHEMA)
    assert any("reference_only" in error for error in errors)


def test_extra_schema_property_fails_closed():
    p = profile()
    document = p.to_dict()
    document["unexpected"] = True
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator, FormatChecker

    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document))
    assert errors


def test_strict_vault_is_required():
    p = profile()
    object.__setattr__(p.vault, "isolation", "shared")
    assert any("strict" in error for error in validate_profile(p, SCHEMA))


def test_invalid_governance_blocks_activation():
    p = profile()
    object.__setattr__(p.governance, "authorization", "automatic")
    report = run_validation_pipeline(p, SCHEMA)
    assert report.valid is False
    assert report.errors


def test_external_execution_is_explicit():
    p = profile()
    assert p.capabilities.external_execution is False
    external = generate_fresh_profile(
        owner_ref="local-owner-001",
        profile_type="custom",
        production_branch="release",
        integration_branch="integration",
        base_vault_dir="/tmp/sovereignty-test",
        external_execution=True,
    )
    assert external.capabilities.external_execution is True


def test_missing_schema_fails_closed(tmp_path: Path):
    report = run_validation_pipeline(profile(), tmp_path / "missing.json")
    assert report.valid is False
    assert report.errors
