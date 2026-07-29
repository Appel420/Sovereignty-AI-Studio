#!/usr/bin/env python3
"""Compute an incremental local-CI scope from Git changes.

The default is conservative: dependency, workflow, build, runtime-map, or CI
changes require the full gate. Ordinary source changes only validate changed
files and changed test modules. Set FULL_CI=1 to force the complete suite.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FULL_MARKERS = (
    "requirements",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "pytest.ini",
    "Makefile",
    "Dockerfile",
    "docker-compose",
    ".github/workflows/",
    "scripts/local-ci.sh",
    "scripts/ci_scope.py",
    "config/runtime-coherence.json",
    "PLATFORM.json",
)


def git_names(*args: str) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def changed_files() -> set[str]:
    names = git_names()
    names |= git_names("--cached")
    base = os.environ.get("BASE_SHA") or os.environ.get("GITHUB_BASE_SHA")
    head = os.environ.get("HEAD_SHA") or os.environ.get("GITHUB_SHA")
    if base and head:
        names |= git_names(f"{base}...{head}")
    elif not names:
        names |= git_names("HEAD~1", "HEAD")
    return {name for name in names if not name.startswith("external/")}


def scope(names: set[str]) -> dict[str, object]:
    full = bool(os.environ.get("FULL_CI")) or any(
        any(name == marker or name.startswith(marker) for marker in FULL_MARKERS)
        for name in names
    )
    python_files = sorted(name for name in names if name.endswith(".py"))
    node_files = sorted(
        name for name in names if name.endswith(('.js', '.mjs', '.cjs'))
    )
    shell_files = sorted(name for name in names if name.endswith(".sh"))
    test_files = sorted(
        name for name in names if name.startswith("tests/") and name.endswith(".py")
    )
    frontend_changed = any(
        name.startswith("frontend/") or name.endswith((".html", ".css"))
        for name in names
    )
    return {
        "full": full,
        "python": python_files,
        "node": node_files,
        "shell": shell_files,
        "tests": test_files,
        "frontend": frontend_changed,
        "changed": sorted(names),
    }


def main() -> int:
    names = changed_files()
    result = scope(names)
    if len(sys.argv) == 1 or sys.argv[1] == "--json":
        import json

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    key = sys.argv[1]
    value = result.get(key)
    if isinstance(value, list):
        print("\n".join(str(item) for item in value))
    elif isinstance(value, bool):
        print("1" if value else "0")
    else:
        print(value or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
