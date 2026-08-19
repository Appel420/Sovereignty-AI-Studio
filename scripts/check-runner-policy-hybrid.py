#!/usr/bin/env python3
"""Validate first-party GitHub Actions runner declarations under the hybrid policy."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path('.github/workflows')
SOVEREIGN = 'self-hosted Linux arm64'
HOSTED = 'ubuntu-latest'
MACOS = {'macos-latest', 'macos-15'}
HYBRID = "${{ vars.SOVEREIGN_CI_RUNNER || 'ubuntu-latest' }}"


def runs_on_values(text: str) -> list[tuple[str, ...]]:
    values: list[tuple[str, ...]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = re.match(r'^\s*runs-on:\s*(.*)$', lines[i])
        if not match:
            i += 1
            continue
        inline = match.group(1).strip()
        if inline:
            labels = tuple(re.findall(r"['\"]([^'\"]+)['\"]", inline))
            values.append(labels or (inline,))
            i += 1
            continue
        labels: list[str] = []
        i += 1
        while i < len(lines):
            item = re.match(r'^\s*-\s*[\'\"]?([^\'\"#]+?)[\'\"]?\s*$', lines[i])
            if not item:
                break
            labels.append(item.group(1).strip())
            i += 1
        values.append(tuple(labels))
    return values


def allowed(labels: tuple[str, ...]) -> bool:
    if len(labels) == 1:
        return labels[0].strip() in {HOSTED, SOVEREIGN, HYBRID} | MACOS
    return labels == (SOVEREIGN,)


def main() -> int:
    if not ROOT.is_dir():
        print('No .github/workflows directory', file=sys.stderr)
        return 1
    invalid: list[str] = []
    checked = 0
    for path in sorted(ROOT.glob('*.y*ml')):
        for labels in runs_on_values(path.read_text(encoding='utf-8')):
            checked += 1
            if not allowed(labels):
                invalid.append(f'INVALID RUNNER: {path}: got {list(labels)!r}')
    if invalid:
        print('\n'.join(invalid), file=sys.stderr)
        return 1
    print(f'Validated {checked} first-party workflow runner declaration(s): hybrid portable policy.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
