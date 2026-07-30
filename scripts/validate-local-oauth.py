#!/usr/bin/env python3
"""Validate the repository-owned offline OAuth contract.

This validator is intentionally local-only. It does not install packages,
contact an issuer, exchange tokens, or invoke any external service.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "local-oauth-policy.json"
GENERATOR = ROOT / "scripts" / "oauth_local_generator.py"


def fail(message: str) -> int:
    print(f"local OAuth validation failed: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not POLICY_PATH.is_file():
        return fail(f"missing policy: {POLICY_PATH}")
    if not GENERATOR.is_file():
        return fail(f"missing canonical generator: {GENERATOR}")

    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy.get("issuer") != "local":
        return fail("issuer must be local")
    if policy.get("generator") != "scripts/oauth_local_generator.py":
        return fail("canonical generator path is incorrect")
    if policy.get("network_access") is not False:
        return fail("network access must be disabled")
    if policy.get("external_oauth") != "disabled":
        return fail("external OAuth must be disabled")

    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--dry-run"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            "PATH": str(Path(sys.executable).parent),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    if result.returncode != 0:
        return fail(f"canonical dry-run failed: {result.stderr.strip()}")

    report = json.loads(result.stdout)
    expected = {
        "issuer": "local",
        "network_accessed": False,
        "validation": "PASS",
        "generation": "SKIPPED",
        "persistence": "SKIPPED",
        "dry_run": True,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            return fail(f"dry-run field {key!r} expected {value!r}, got {report.get(key)!r}")

    print("local OAuth contract passed")
    print(f"canonical generator: {policy['generator']}")
    print("network access: disabled")
    print("external OAuth: disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
