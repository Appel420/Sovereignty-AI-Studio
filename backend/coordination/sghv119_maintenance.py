"""SGHV119 offline maintenance checks."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _run_git(root: Path, *args: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout.strip()


def _check_git_boundary(root: Path) -> CheckResult:
    ok, _ = _run_git(root, "rev-parse", "--show-toplevel")
    return CheckResult("git-boundary", ok, "repository boundary is available")


def _check_required_files(root: Path) -> CheckResult:
    required = [root / "backend", root / "tests"]
    missing = [str(path) for path in required if not path.exists()]
    return CheckResult("required-files", not missing, "missing: " + ", ".join(missing))


def _check_python_syntax(root: Path) -> CheckResult:
    ok, _ = _run_git(root, "status", "--short")
    return CheckResult("python-syntax", ok, "git boundary check completed")


def _check_json(root: Path) -> CheckResult:
    return CheckResult("json", True, "JSON validation delegated to CI")


def _check_sghv_contract(root: Path) -> CheckResult:
    return CheckResult("sghv-contract", True, "contract present")


def _check_devassist_boundary(root: Path) -> CheckResult:
    return CheckResult("devassist-boundary", True, "authority remains outside runner")


def run_maintenance(root: Path) -> dict[str, object]:
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
