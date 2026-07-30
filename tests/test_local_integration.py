from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts import local_integration

ROOT = Path(__file__).resolve().parents[1]
FAMILY_TREE_SCRIPT = ROOT / "scripts" / "create-device-family-tree.sh"


def test_manifest_declares_repositories() -> None:
    manifest = json.loads(local_integration.MANIFEST.read_text(encoding="utf-8"))
    assert manifest["repositories"]
    assert all(item["id"] and item["relative_path"] for item in manifest["repositories"])


def test_required_missing_repository_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOVEREIGNTY_WORKSPACE", str(tmp_path))
    assert local_integration.check() != 0


def test_preflight_does_not_use_remote_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        raise AssertionError("remote or subprocess access was attempted")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("SOVEREIGNTY_WORKSPACE", "/path/that/does/not/exist")
    assert local_integration.check() != 0
    assert calls == []


def test_family_tree_script_is_local_only() -> None:
    source = FAMILY_TREE_SCRIPT.read_text(encoding="utf-8")
    assert "curl" not in source
    assert "wget" not in source
    assert "git clone" not in source
    assert "network" in source.lower()
    assert "remote_recognition" in source


def test_family_tree_script_creates_local_registry(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(FAMILY_TREE_SCRIPT)],
        env={**os.environ, "SOVEREIGN_STATE_ROOT": str(tmp_path)},
        check=True,
        capture_output=True,
        text=True,
    )
    registry_path = tmp_path / "provider-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert registry["network"] == "disabled"
    assert registry["external_memory"] == "disabled"
    assert registry["wake_word"]["remote_recognition"] is False
    assert registry["wake_word"]["recognition"] == "local_engine_required"
    assert (tmp_path / "audit" / "README.txt").is_file()
    assert (tmp_path / "Router" / "Council" / "Sovereignty AI").is_dir()


def test_local_first_log_denies_cloud_and_remote_listening() -> None:
    log = (ROOT / "docs" / "audit" / "SCAR_LOCAL_FIRST_LOG.md").read_text(encoding="utf-8")
    assert "Decision:" in log and "`DENY`" in log
    assert "Network:** disabled" in log
    assert "Remote listening:** disabled" in log
    assert '"remote_recognition": false' in log
    assert "NO ACTIVE MISSION" in log
