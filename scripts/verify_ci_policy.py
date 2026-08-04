#!/usr/bin/env python3
"""Enforce the manual-only GitHub Actions policy for first-party workflows."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
FORBIDDEN = re.compile(r"^\s*(pull_request|push|schedule)\s*:")


def main() -> int:
    failures: list[str] = []
    for path in sorted(WORKFLOWS.glob("*")):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FORBIDDEN.match(line):
                failures.append(f"{path.relative_to(ROOT)}:{line_no}: automatic trigger is disabled by policy: {line.strip()}")

    if failures:
        print("CI POLICY VIOLATION", file=sys.stderr)
        print("\n".join(f"- {item}" for item in failures), file=sys.stderr)
        return 1

    print("CI policy passed: workflow_dispatch-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
