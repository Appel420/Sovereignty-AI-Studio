"""Tests for incremental CI scope detection."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "ci_scope.py"
SPEC = importlib.util.spec_from_file_location("ci_scope", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_dependency_changes_require_full_ci() -> None:
    result = MODULE.scope({"pyproject.toml"})
    assert result["full"] is True


def test_source_changes_are_incremental() -> None:
    result = MODULE.scope({"backend/coordination/devassist_router.py"})
    assert result["full"] is False
    assert result["python"] == ["backend/coordination/devassist_router.py"]


def test_external_changes_are_excluded_from_runtime_scope() -> None:
    result = MODULE.scope(set())
    assert "external/vendor/file.py" not in result["changed"]
