#!/usr/bin/env python3
"""Enforce supported workflow triggers for global CI."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
FORBIDDEN = re.compile(r"^\s*schedule\s*:")
ALLOWED = re.compile(r"^\s*(workflow_dispatch|push|pull_request)\s*:")


def main() -> int:
    failures: list[str] = []
    for path in sorted(WORKFLOWS.glob("*")):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FORBIDDEN.match(line):
                failures.append(f"{path.relative_to(ROOT)}:{line_no}: scheduled execution is not permitted: {line.strip()}")
            elif line.lstrip() and not line.startswith(" ") and not line.startswith("\t"):
                # This script only validates known top-level trigger declarations.
                if re.match(r"^\s*(push|pull_request|workflow_dispatch)\s*:", line):
                    continue

    if failures:
        print("CI POLICY VIOLATION", file=sys.stderr)
        print("\n".join(f"- {item}" for item in failures), file=sys.stderr)
        return 1

    print("CI policy passed: workflow_dispatch, push, and pull_request triggers supported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
