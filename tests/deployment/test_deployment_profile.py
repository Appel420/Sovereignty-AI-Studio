from __future__ import annotations

from pathlib import Path
import tempfile

from src.deployment.deployment_profile import generate_fresh_profile, run_validation_pipeline, validate_profile

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
    assert validate_profile(profile, SCHEMA) == []
    report = run_validation_pipeline(profile, SCHEMA)
    assert report.valid is True
    assert report.owner_approval_required is True


def test_topology_has_no_personal_defaults():
    profile = make_profile()
    assert profile.topology.production_branch == "production"
    assert profile.topology.integration_branch == "integration"
    assert profile.topology.development_lanes == []
    assert profile.topology.agents == []
    assert profile.topology.providers == []


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


def test_external_execution_is_explicit():
    assert make_profile().capabilities.external_execution is False
    assert make_profile(external_execution=True).capabilities.external_execution is True


def test_missing_schema_fails_closed(tmp_path: Path):
    report = run_validation_pipeline(make_profile(), tmp_path / "missing.json")
    assert report.valid is False
    assert report.errors
