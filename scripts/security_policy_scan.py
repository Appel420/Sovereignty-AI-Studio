#!/usr/bin/env python3
"""Zero-tolerance scan for governed security paths."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Finding:
    path: Path
    category: str
    pattern: str
    rule: str


def load_policy(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        policy = json.load(handle)
    if not isinstance(policy, dict):
        raise ValueError("security policy must be a JSON object")
    return policy


def validate_policy(policy: dict[str, Any]) -> None:
    required = {"policy_id", "enforcement", "protected_paths", "forbidden_patterns"}
    missing = sorted(required.difference(policy))
    if missing:
        raise ValueError(f"missing policy fields: {', '.join(missing)}")
    enforcement = policy["enforcement"]
    if not isinstance(enforcement, dict) or enforcement.get("mode") != "deny":
        raise ValueError("security policy must use deny mode")
    if enforcement.get("fail_ci") is not True:
        raise ValueError("security policy must set fail_ci=true")
    paths = policy["protected_paths"]
    if not isinstance(paths, list) or not all(isinstance(item, str) and item.strip() for item in paths):
        raise ValueError("protected_paths must contain non-empty strings")
    entries = policy["forbidden_patterns"]
    if not isinstance(entries, list):
        raise ValueError("forbidden_patterns must be a list")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("category"), str):
            raise ValueError("each forbidden-pattern entry needs a category")
        if not isinstance(entry.get("rule"), str) or not entry["rule"].strip():
            raise ValueError("each forbidden-pattern entry needs a rule")
        patterns = entry.get("patterns")
        if not isinstance(patterns, list) or not all(isinstance(pattern, str) and pattern for pattern in patterns):
            raise ValueError("each forbidden-pattern entry needs non-empty patterns")


def collect_targets(root: Path, protected_paths: list[str]) -> list[Path]:
    targets: set[Path] = set()
    for relative in protected_paths:
        directory = (root / relative).resolve()
        if not directory.is_dir() or root.resolve() not in directory.parents and directory != root.resolve():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and not any(part in {".git", ".venv", "__pycache__", "node_modules"} for part in path.parts):
                targets.add(path)
    return sorted(targets)


def scan_file(path: Path, patterns: list[str]) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return []
    return [pattern for pattern in patterns if pattern in content]


def scan(root: Path, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for path in collect_targets(root, policy["protected_paths"]):
        for entry in policy["forbidden_patterns"]:
            for pattern in scan_file(path, entry["patterns"]):
                findings.append(Finding(path, entry["category"], pattern, entry["rule"]))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan governed security paths")
    parser.add_argument("policy", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.policy)
        validate_policy(policy)
        findings = scan(args.root.resolve(), policy)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ZERO_TOLERANCE_INVALID_POLICY: {error}")
        return 2
    if findings:
        print("ZERO_TOLERANCE_VIOLATIONS")
        for finding in findings:
            print(f"{finding.path}: [{finding.category}] {finding.pattern} — {finding.rule}")
        return 1
    print("ZERO_TOLERANCE_OK")
    print("classification=policy_scan_only; production_attestation=not_performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
