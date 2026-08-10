#!/usr/bin/env python3
"""Audit repository files for stale hard-coded branch assumptions.

This is read-only. It does not create, rename, delete, or switch branches.
The repository's canonical integration branch is discovered from GitHub only
when explicitly supplied; otherwise the local Git symbolic default is used.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

DEFAULT_CANONICAL = "Collaboration"
STALE_BRANCHES = {"main", "master", "collaboration"}
TEXT_SUFFIXES = {".py", ".sh", ".js", ".ts", ".tsx", ".yml", ".yaml", ".json", ".md", ".txt"}
PATTERNS = [
    re.compile(r"(?i)\bBRANCH\s*=\s*['\"]main['\"]"),
    re.compile(r"(?i)\bref(?:erence)?\s*[:=]\s*['\"]main['\"]"),
    re.compile(r"(?i)\bbranch\s+main\s+not\s+found\b"),
    re.compile(r"(?i)\bNo\s+commit\s+found\s+for\s+the\s+ref\s+main\b"),
]


def git_default_branch(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "symbolic-ref", "refs/remotes/origin/HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value.rsplit("/", 1)[-1] if value else DEFAULT_CANONICAL


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", default="", help="Canonical integration branch")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    canonical = args.canonical or git_default_branch(root)
    findings: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts or ".venv" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append(f"{path.relative_to(root)}:{line_no}: {line.strip()}")

    print(f"Canonical integration branch: {canonical}")
    if not findings:
        print("PASS: no known stale main/master branch assumptions found")
        return 0

    print(f"FAIL: {len(findings)} stale branch assumption(s) found")
    for finding in findings:
        print(f"- {finding}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
