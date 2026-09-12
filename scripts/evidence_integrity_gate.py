#!/usr/bin/env python3
"""Detect runtime/UI claims that are not backed by observed evidence.

This is deliberately conservative: a finding is a FAIL, not an inferred PASS.
The gate scans runtime-facing source only. Documentation and historical artifacts
are excluded so examples do not become runtime evidence.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

RUNTIME_SUFFIXES = {".html", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".py"}
EXCLUDED = {".git", "node_modules", "dist", "build", "venv", ".venv", "__pycache__"}

PATTERNS = (
    (re.compile(r"\bid=['\"]systemStatus['\"]\s*>\s*(?:OPERATIONAL|PASS|VERIFIED|HEALTHY)", re.I), "hard-coded success state in UI"),
    (re.compile(r"['\"](?:systemStatus|status)['\"]\s*[:=]\s*['\"](?:OPERATIONAL|PASS|VERIFIED|HEALTHY)['\"]", re.I), "hard-coded success state"),
    (re.compile(r"title\s*[:=]\s*['\"][^'\"]*(?:Compliance|TPM|Uptime|Performance)\s*:\s*\d+(?:\.\d+)?%?", re.I), "hard-coded metric"),
    (re.compile(r"Compliance\s*:\s*98\.7%", re.I), "hard-coded compliance metric"),
    (re.compile(r"TPM\s*:\s*100(?:\.0)?%?", re.I), "hard-coded TPM metric"),
    (re.compile(r"uptime\s*:\s*99\.9", re.I), "hard-coded uptime metric"),
    (re.compile(r"performance\s*:\s*94\.2", re.I), "hard-coded performance metric"),
    (re.compile(r"Threat feed updated\s*\(\s*1,247", re.I), "static threat-feed claim"),
    (re.compile(r"TPM validation completed\s*-\s*PASS", re.I), "unproven hardware-attestation claim"),
    (re.compile(r"\bstartSimulation\s*\(", re.I), "simulation path exposed as runtime validation"),
    (re.compile(r"\bpopulateInitialLogs\s*\(", re.I), "synthetic logs presented as runtime evidence"),
)


def files(root: pathlib.Path):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in RUNTIME_SUFFIXES and not any(x in EXCLUDED for x in p.parts):
            yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()
    if not root.is_dir() or root == pathlib.Path(root.anchor):
        print("EVIDENCE INTEGRITY: DENY — unsafe or invalid repository root", file=sys.stderr)
        return 2

    findings = []
    for p in files(root):
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(lines, 1):
            for rx, reason in PATTERNS:
                if rx.search(line):
                    findings.append((p.relative_to(root), n, reason))

    if findings:
        print("EVIDENCE INTEGRITY: DENY")
        print("Unverified runtime/UI state was detected. No success state is inferred.")
        for path, line, reason in findings:
            print(f"{path}:{line}: {reason}")
        return 1

    print("EVIDENCE INTEGRITY: PASS")
    print("No high-confidence fabricated runtime/UI claims detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
