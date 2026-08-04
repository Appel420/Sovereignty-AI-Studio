#!/usr/bin/env python3
"""Validate that the local dashboard has its offline build inputs."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/apple_m4_neural.md",
    "scripts/validate-local-oauth.py",
    "scripts/validate-local-state.sh",
    "scripts/local-ci.sh",
    "config/local-oauth-policy.json",
    "bridge/local_dashboard_status.py",
    "bridge/serve_dashboard.py",
)
OPTIONAL_ANY = (
    ("scripts/validate-local-state.sh", "validate-local-state.sh"),
    ("scripts/local-ci.sh", "scripts/v1_local-ci.sh", "v1_local-ci.sh"),
    ("scripts/oauth_local_generator.py", "oauth_local_generator.py"),
)


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]

    for group in OPTIONAL_ANY:
        if not any((ROOT / path).is_file() for path in group):
            missing.append(" OR ".join(group))

    if missing:
        for path in missing:
            print(f"missing local dashboard build input: {path}")
        return 1

    print("local dashboard build inputs passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
