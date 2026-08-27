"""Tests for offline incremental CI scope detection."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "ci_scope.py"
SPEC = importlib.util.spec_from_file_location("ci_scope", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_dependency_changes_require_full_ci():
    assert MODULE.scope({"pyproject.toml"})["full"] is True


def test_source_changes_are_incremental(): 
    result = MODULE.scope({"backend/coordination/devassist_router.py"})
    assert result["full"] is True
    assert result["python"] == ["backend/coordination/devassist_router.py"]


def test_vendor_changes_are_excluded():
    result = MODULE.scope({"external/vendor/file.py"})
    assert result["changed"] == []
    assert result["python"] == []
    assert result["full"] is True


def test_scope_has_no_install_or_network_policy():
    text = Path("scripts/local-ci.sh").read_text(encoding="utf-8")
    assert "pip install" not in text
    assert "npm install" not in text
    assert "curl " not in text
    assert "PIP_NO_INDEX" in text
    assert "SG_NETWORK_MODE=local" in text
