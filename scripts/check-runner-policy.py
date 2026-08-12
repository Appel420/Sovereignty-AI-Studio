#!/usr/bin/env python3
"""Validate self-hosted Linux ARM64 runner labels in first-party workflows."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(".github/workflows")
REQUIRED = ("self-hosted Linux arm64",)


def _runs_on_values(text: str) -> list[tuple[str, ...]]:
    """Extract runs-on labels without requiring a YAML dependency."""
    values: list[tuple[str, ...]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^\s*runs-on:\s*(.*)$", lines[index])
        if not match:
            index += 1
            continue

        inline = match.group(1).strip()
        if inline:
            labels = tuple(re.findall(r"['\"]([^'\"]+)['\"]", inline))
            if not labels:
                labels = (inline,)
            values.append(labels)
            index += 1
            continue

        labels: list[str] = []
        index += 1
        while index < len(lines):
            label_match = re.match(r"^\s*-\s*['\"]?([^'\"#]+?)['\"]?\s*$", lines[index])
            if not label_match:
                break
            labels.append(label_match.group(1).strip())
            index += 1
        values.append(tuple(labels))
    return values


def main() -> int:
    if not ROOT.is_dir():
        print("No .github/workflows directory", file=sys.stderr)
        return 1

    invalid: list[str] = []
    checked = 0
    for path in sorted(ROOT.glob("*.y*ml")):
        for labels in _runs_on_values(path.read_text(encoding="utf-8")):
            if "self-hosted" not in labels and labels != REQUIRED:
                continue
            checked += 1
            if labels != REQUIRED:
                invalid.append(
                    f"INVALID SELF-HOSTED RUNNER: {path}: expected {list(REQUIRED)!r}, got {list(labels)!r}"
                )

    if invalid:
        print("\n".join(invalid), file=sys.stderr)
        return 1

    print(f"Validated {checked} self-hosted workflow runner declaration(s): self-hosted Linux arm64.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
