from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from src.deployment import deployment_profile as module
from src.deployment.deployment_profile import (
    DeploymentProfile,
    ValidationError,
    generate_fresh_profile,
    run_validation_pipeline,
    save_profile,
    validate_profile,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "docs" / "deployment" / "deployment-profile.schema.json"


def make_profile(**overrides):
    values = {
        "owner_ref": "local-owner-ref",
        "profile_type": "personal",
        "production_branch": "production",
        "integration_branch": "integration",
        "base_vault_dir": str(Path(tempfile.gettempdir()) / "sovereignty-test"),
    }
    values.update(overrides)
    return generate_fresh_profile(**values)


def test_fresh_profile_validates():
    profile = make_profile()
    assert isinstance(profile, DeploymentProfile)
    assert validate_profile(profile, SCHEMA) == []
    report = run_validation_pipeline(profile, SCHEMA)
    assert report.valid is True
    assert report.errors == []
    assert report.owner_approval_required is True
    assert "owner_approval_required" in report.steps_completed


def test_topology_has_no_personal_defaults():
    profile = make_profile()
    assert profile.topology.production_branch == "production"
    assert profile.topology.integration_branch == "integration"
    assert profile.topology.development_lanes == []
    assert profile.topology.agents == []
    assert profile.topology.providers == []


def test_generated_identity_values_are_distinct():
    profile = make_profile()
    values = {
        profile.identity.owner_ref,
        profile.identity.device_id,
        profile.identity.authority_id,
    }
    assert len(values) == 3
    assert len(profile.identity.device_id) >= 16
    assert len(profile.identity.authority_id) >= 16


def test_reference_profile_cannot_activate():
    profile = make_profile(reference_only=True)
    report = run_validation_pipeline(profile, SCHEMA)
    assert report.valid is False
    assert any("reference_only" in error for error in report.errors)


def test_governance_is_fail_closed():
    profile = make_profile()
    object.__setattr__(profile.governance, "authorization", "automatic")
    report = run_validation_pipeline(profile, SCHEMA)
    assert report.valid is False
    assert any("governance.authorization" in error for error in report.errors)


def test_external_execution_is_explicit():
    assert make_profile().capabilities.external_execution is False
    assert make_profile(external_execution=True).capabilities.external_execution is True


def test_missing_schema_fails_closed(tmp_path: Path):
    report = run_validation_pipeline(make_profile(), tmp_path / "missing.json")
    assert report.valid is False
    assert report.errors
    assert report.errors[0].startswith("schema unavailable:")


def test_schema_additional_property_is_rejected():
    profile = make_profile()
    data = profile.to_dict()
    data["unexpected"] = True
    errors = module._validate_schema_contract(
        data,
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )
    assert any("additional property" in error for error in errors)


def test_schema_version_is_enforced():
    profile = make_profile()
    object.__setattr__(profile.deployment, "schema_version", "0.0.0")
    errors = validate_profile(profile, SCHEMA)
    assert any("schema_version" in error for error in errors)


def test_minimal_schema_fallback_enforces_schema_contract(monkeypatch):
    monkeypatch.setattr(module, "Draft202012Validator", None)
    monkeypatch.setattr(module, "FormatChecker", None)
    profile = make_profile()
    object.__setattr__(profile.deployment, "schema_version", "0.0.0")
    errors = module.validate_profile(profile, SCHEMA)
    assert any("schema_version" in error for error in errors)


def test_minimal_schema_fallback_rejects_additional_property(monkeypatch):
    monkeypatch.setattr(module, "Draft202012Validator", None)
    monkeypatch.setattr(module, "FormatChecker", None)
    profile = make_profile()
    data = profile.to_dict()
    data["unexpected"] = True
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = module._minimal_schema_errors(data, schema)
    assert any("additional property" in error for error in errors)


def test_minimal_schema_fallback_rejects_invalid_datetime(monkeypatch):
    monkeypatch.setattr(module, "Draft202012Validator", None)
    monkeypatch.setattr(module, "FormatChecker", None)
    profile = make_profile()
    object.__setattr__(profile.deployment, "created_at", "not-a-date")
    errors = module.validate_profile(profile, SCHEMA)
    assert any("created_at" in error for error in errors)


def test_state_and_evidence_collision_is_rejected():
    profile = make_profile()
    object.__setattr__(profile.vault, "evidence_path", profile.vault.state_path)
    errors = validate_profile(profile, SCHEMA)
    assert any("state_path and evidence_path collide" in error for error in errors)


def test_state_and_evidence_normalized_collision_is_rejected():
    profile = make_profile()
    state = Path(profile.vault.state_path)
    equivalent = state.parent / "." / state.name
    object.__setattr__(profile.vault, "evidence_path", str(equivalent))
    errors = validate_profile(profile, SCHEMA)
    assert any("state_path and evidence_path collide" in error for error in errors)


def test_invalid_profile_type_is_rejected():
    with pytest.raises(ValidationError):
        make_profile(profile_type="invalid")


def test_short_owner_reference_is_rejected():
    with pytest.raises(ValidationError):
        make_profile(owner_ref="short")


def test_email_like_owner_reference_is_rejected():
    with pytest.raises(ValidationError):
        make_profile(owner_ref="owner@example")


def test_missing_branch_is_rejected():
    with pytest.raises(ValidationError):
        make_profile(production_branch="")


def test_duplicate_topology_values_are_rejected():
    profile = make_profile(agents=["agent-a", "agent-a"])
    errors = validate_profile(profile, SCHEMA)
    assert any("topology.agents contains duplicates" in error for error in errors)


def test_profile_serialization_is_deterministic():
    profile = make_profile()
    first = profile.to_json()
    second = json.dumps(profile.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
    assert first == second


def test_save_profile_round_trip(tmp_path: Path):
    profile = make_profile()
    destination = tmp_path / "deployment-profile.json"
    save_profile(profile, destination)
    assert destination.is_file()
    restored = json.loads(destination.read_text(encoding="utf-8"))
    assert restored == profile.to_dict()


def test_save_profile_creates_parent_directories(tmp_path: Path):
    profile = make_profile()
    destination = tmp_path / "nested" / "deployment" / "profile.json"
    save_profile(profile, destination)
    assert destination.is_file()


def test_save_profile_rejects_wrong_type(tmp_path: Path):
    with pytest.raises(ValidationError):
        save_profile(object(), tmp_path / "profile.json")  # type: ignore[arg-type]


def test_validation_never_grants_owner_approval():
    profile = make_profile()
    report = run_validation_pipeline(profile, SCHEMA)
    assert report.owner_approval_required is True
    assert "owner_approval_required" in report.steps_completed


def test_reference_only_profile_is_never_valid():
    profile = make_profile(reference_only=True)
    assert validate_profile(profile, SCHEMA)


def test_invalid_governance_promotion_blocks_validation():
    profile = make_profile()
    object.__setattr__(profile.governance, "promotion", "automatic")
    errors = validate_profile(profile, SCHEMA)
    assert any("governance.promotion" in error for error in errors)
