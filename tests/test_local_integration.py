from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts import local_integration


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
