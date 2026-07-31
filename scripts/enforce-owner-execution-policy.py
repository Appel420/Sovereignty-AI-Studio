#!/usr/bin/env python3
"""Fail closed when owner-approved local execution requirements are violated."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/owner-execution-policy.json"
WORKFLOWS = ROOT / ".github/workflows"
EXPECTED_RUNNER = "['self-hosted Linux arm64']"


def main() -> int:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    failures: list[str] = []

    if policy.get("cloud_allowed") is not False:
        failures.append("cloud_allowed must be false")
    if policy.get("cloud_first") is not False:
        failures.append("cloud_first must be false")
    if policy.get("pull_request_hosted_dependencies") is not False:
        failures.append("pull_request_hosted_dependencies must be false")
    if policy.get("required_runner") != ["self-hosted Linux arm64"]:
        failures.append("required runner must be self-hosted Linux arm64")

    for path in sorted(WORKFLOWS.glob("*")):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            match = re.match(r"^\s*runs-on:\s*(.+)$", line)
            if match and match.group(1).strip() != EXPECTED_RUNNER:
                failures.append(f"{path}:{line_no}: forbidden runner {match.group(1).strip()}")

    if failures:
        print("OWNER POLICY VIOLATION", file=sys.stderr)
        print("\n".join(f"- {item}" for item in failures), file=sys.stderr)
        return 1

    print("owner execution policy passed")
    print("local-first: enforced")
    print("cloud-first: prohibited")
    print("PR hosted dependency checks: prohibited")
    print("runner: self-hosted Linux arm64")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
