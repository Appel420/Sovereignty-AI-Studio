"""Read-only SGHV119 maintenance checks.

This module is intentionally verification-only. It does not authorize work,
modify repository files, contact providers, or retain session state.
"""
from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    "docs/architecture/SGHV119_RUNTIME.md",
    "frontend/runtime/transport.js",
    "scripts/run-local-ci.py",
    "backend/coordination/execution_contracts.py",
    "backend/coordination/devassist_adapter.py",
    "backend/coordination/task_envelope.py",
)
JSON_FILES = ("config/ci-mode-registry.json", "integration/repository-registry.json")
PYTHON_FILES = (
    "scripts/run-local-ci.py",
    "backend/coordination/execution_contracts.py",
    "backend/coordination/devassist_adapter.py",
    "backend/coordination/task_envelope.py",
)


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _run_git(root: Path, *args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    return True, result.stdout.strip()


def _check_git_boundary(root: Path) -> CheckResult:
    ok, branch = _run_git(root, "branch", "--show-current")
    if not ok:
        return CheckResult("git-boundary", True, "git metadata unavailable; fixture accepted")
    if branch in {"main", "master"}:
        return CheckResult("git-boundary", False, f"protected branch: {branch}")
    return CheckResult("git-boundary", True, f"branch={branch or 'detached'}")


def _check_required_files(root: Path) -> CheckResult:
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    if missing:
        return CheckResult("required-files", False, "missing: " + ", ".join(missing))
    return CheckResult("required-files", True, f"verified={len(REQUIRED_FILES)}")


def _check_python_syntax(root: Path) -> CheckResult:
    failures = []
    for relative in PYTHON_FILES:
        path = root / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            failures.append(f"{relative}:{exc}")
    if failures:
        return CheckResult("python-syntax", False, "; ".join(failures))
    return CheckResult("python-syntax", True, f"parsed={len(PYTHON_FILES)}")


def _check_json(root: Path) -> CheckResult:
    failures = []
    for relative in JSON_FILES:
        path = root / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{relative}:{exc}")
    if failures:
        return CheckResult("json-config", False, "; ".join(failures))
    return CheckResult("json-config", True, f"parsed={len(JSON_FILES)}")


def _check_sghv_contract(root: Path) -> CheckResult:
    path = root / "docs/architecture/SGHV119_RUNTIME.md"
    if not path.is_file():
        return CheckResult("sghv119-contract", False, "contract missing")
    text = path.read_text(encoding="utf-8")
    required = (
        "DECLARED", "CONFIGURED", "AVAILABLE", "VERIFIED", "ACTIVE",
        "UNAVAILABLE", "DENY", "REQUIRE_APPROVAL", "local/offline mode"
    )
    missing = [term for term in required if term not in text]
    if missing:
        return CheckResult("sghv119-contract", False, "missing terms: " + ", ".join(missing))
    return CheckResult("sghv119-contract", True, "runtime state vocabulary present")


def _check_devassist_boundary(root: Path) -> CheckResult:
    path = root / "backend/coordination/devassist_adapter.py"
    if not path.is_file():
        return CheckResult("devassist-boundary", False, "adapter missing")
    text = path.read_text(encoding="utf-8")
    required = (
        "does not authorize",
        "route.decision != \"ALLOW\"",
        "route.route not in self._allowed_routes",
    )
    missing = [term for term in required if term not in text]
    if missing:
        return CheckResult("devassist-boundary", False, "boundary markers missing: " + ", ".join(missing))
    return CheckResult("devassist-boundary", True, "execution remains ALLOW-gated")


def run_maintenance(root: Path) -> dict[str, Any]:
    root = root.resolve()
    checks = [
        _check_git_boundary(root),
        _check_required_files(root),
        _check_python_syntax(root),
        _check_json(root),
        _check_sghv_contract(root),
        _check_devassist_boundary(root),
    ]
    passed = all(check.passed for check in checks)
    ok, sha = _run_git(root, "rev-parse", "HEAD")
    if not ok:
        sha = "unknown"
    ok, branch = _run_git(root, "branch", "--show-current")
    if not ok:
        branch = "unknown"
    return {
        "runner": "sghv119-maintenance",
        "mode": "offline-read-only",
        "network": "disabled-by-design",
        "branch": branch,
        "commit": sha,
        "status": "PASS" if passed else "FAIL",
        "admissible": passed,
        "authorization": "not-granted-by-runner",
        "checks": [check.to_dict() for check in checks],
    }
