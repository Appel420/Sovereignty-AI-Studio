#!/usr/bin/env python3
"""Enforce owner runner policy: self-hosted Linux arm64 only."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED = "['self-hosted Linux arm64']"
ROOT = Path(".github/workflows")


def main() -> int:
    if not ROOT.is_dir():
        print("No .github/workflows directory", file=sys.stderr)
        return 1

    invalid = []
    for path in sorted(ROOT.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"(?m)^\s*runs-on:\s*(.+)$", text):
            value = match.group(1).strip()
            if value != REQUIRED:
                invalid.append(f"INVALID RUNNER: {path}: {value}")

    if invalid:
        for line in invalid:
            print(line, file=sys.stderr)
        return 1

    print("All first-party workflows use self-hosted Linux arm64.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
