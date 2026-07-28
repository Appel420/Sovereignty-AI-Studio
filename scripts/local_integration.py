#!/usr/bin/env python3
"""Offline-first local integration preflight for the Sovereignty workspace."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "integration" / "local-repositories.json"


def workspace() -> Path:
    configured = os.environ.get("SOVEREIGNTY_WORKSPACE")
    return Path(configured).expanduser() if configured else Path.home() / "Sovereignty"


def run_git(path: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def check() -> int:
    with MANIFEST.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    base = workspace()
    failures = 0
    print(f"workspace: {base}")
    print("network: not used by preflight")

    for repository in manifest["repositories"]:
        path = base / repository["relative_path"]
        exists = path.is_dir()
        git_root = run_git(path, "rev-parse", "--show-toplevel") if exists else None
        status = "OK" if git_root else "MISSING"
        required = "required" if repository["required"] else "optional"
        print(f"{status:7} {required:8} {repository['id']:14} {path}")
        if repository["required"] and not git_root:
            failures += 1

    if not (ROOT / "docs" / "SOVEREIGNTY_AI_SPECIFICATION_v1.0.md").is_file():
        print("MISSING required normative specification")
        failures += 1
    if not (ROOT / "integration" / "local-repositories.json").is_file():
        print("MISSING integration manifest")
        failures += 1

    if failures:
        print(f"preflight: FAIL ({failures} required checks)")
        return 1
    print("preflight: PASS")
    return 0


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "check":
        print("usage: python3 scripts/local_integration.py check", file=sys.stderr)
        return 2
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
