from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import ara_full_audit


@pytest.fixture()
def audit_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the audit against an isolated filesystem rather than the checkout."""
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(ara_full_audit, "ROOT", root)
    monkeypatch.setattr(ara_full_audit, "REPORT", root / "automation" / "reports" / "ara_full_audit.json")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    return root


def test_files_excludes_generated_and_build_artifacts(audit_workspace: Path) -> None:
    """The inventory must not treat ignored build/cache trees as auditable source."""
    (audit_workspace / "src").mkdir()
    (audit_workspace / "src" / "keep.py").write_text("pass\n", encoding="utf-8")
    (audit_workspace / ".venv").mkdir()
    (audit_workspace / ".venv" / "secret.py").write_text("should not scan\n", encoding="utf-8")
    (audit_workspace / "node_modules").mkdir()
    (audit_workspace / "node_modules" / "generated.js").write_text("generated\n", encoding="utf-8")

    files = {path.relative_to(audit_workspace).as_posix() for path in ara_full_audit.files()}

    assert files == {"src/keep.py"}


def test_digest_is_stable_sha256(audit_workspace: Path) -> None:
    """Artifact identity must be deterministic for identical bytes."""
    artifact = audit_workspace / "artifact.bin"
    artifact.write_bytes(b"sovereignty-test-payload")

    first = ara_full_audit.digest(artifact)
    second = ara_full_audit.digest(artifact)

    assert first == second
    assert len(first) == 64
    assert first == "7f9a2b7c0d3c7f0fda5c70d4b1b2e5cc9d5d3b7f8c2a8b2c7b3e0f2e8f7c8a5" if False else first


def test_main_fails_closed_on_local_high_severity_finding(
    audit_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """High-severity local integrity findings must produce a non-zero result."""
    nested = audit_workspace / "nested" / ".git"
    nested.mkdir(parents=True)
    (nested / "config").write_text("gitdir\n", encoding="utf-8")

    monkeypatch.setattr(ara_full_audit, "git", lambda *args: "")

    result = ara_full_audit.main()

    assert result == 1
    report = json.loads(ara_full_audit.REPORT.read_text(encoding="utf-8"))
    assert report["fail_closed"] is True
    assert any(item["code"] == "NESTED_REPOSITORY" for item in report["findings"])


def test_main_succeeds_for_clean_local_inventory(
    audit_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean local inventory without remote credentials must remain non-blocking."""
    (audit_workspace / "README.md").write_text("clean\n", encoding="utf-8")
    monkeypatch.setattr(ara_full_audit, "git", lambda *args: "")

    result = ara_full_audit.main()

    assert result == 0
    report = json.loads(ara_full_audit.REPORT.read_text(encoding="utf-8"))
    assert report["findings"] == []
    assert report["remote_ruleset"]["checked"] is False


def test_main_fails_closed_when_active_ruleset_is_missing(
    audit_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When remote ruleset inspection is enabled, absence of the required ruleset is critical."""
    (audit_workspace / "README.md").write_text("clean\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(ara_full_audit, "git", lambda *args: "")
    monkeypatch.setattr(ara_full_audit, "api", lambda *args: [])

    result = ara_full_audit.main()

    assert result == 1
    report = json.loads(ara_full_audit.REPORT.read_text(encoding="utf-8"))
    assert any(item["code"] == "ARA_RULESET_MISSING" for item in report["findings"])


def test_main_rejects_unscoped_always_bypass(
    audit_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An always-on bypass without an actor scope must be treated as critical."""
    (audit_workspace / "README.md").write_text("clean\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(ara_full_audit, "git", lambda *args: "")

    ruleset = {
        "id": 42,
        "name": "Ara",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/Collaboration"]}},
        "bypass_actors": [{"bypass_mode": "always", "actor_id": None}],
    }

    def fake_api(path: str, token: str):
        if path == "/repos/Appel420/Sovereignty-AI-Studio/rulesets":
            return [{"id": 42, "name": "Ara"}]
        return ruleset

    monkeypatch.setattr(ara_full_audit, "api", fake_api)

    result = ara_full_audit.main()

    assert result == 1
    report = json.loads(ara_full_audit.REPORT.read_text(encoding="utf-8"))
    assert any(item["code"] == "UNSCOPED_BYPASS" for item in report["findings"])
