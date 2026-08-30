#!/usr/bin/env python3
"""Repository gate for the frozen I-008 contract."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "option-set-with-risk-reward.schema.json"


def main() -> int:
    if not SCHEMA_PATH.is_file():
        print(f"FAIL: missing canonical schema: {SCHEMA_PATH}", file=sys.stderr)
        return 1
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        print(f"FAIL: invalid I-008 schema: {exc}", file=sys.stderr)
        return 1

    required = set(schema.get("properties", {}).get("options", {}).get("items", {}).get("required", []))
    expected = {"id", "label", "pros", "cons", "risks", "rewards"}
    if not expected.issubset(required):
        print(f"FAIL: I-008 option contract missing required fields: {sorted(expected - required)}", file=sys.stderr)
        return 1

    module = ROOT / "backend" / "coordination" / "i008_transparency.py"
    tests = ROOT / "tests" / "test_i008_transparency.py"
    for path in (module, tests):
        if not path.is_file():
            print(f"FAIL: missing I-008 enforcement artifact: {path}", file=sys.stderr)
            return 1

    print("I008_SCHEMA=VALID")
    print("I008_REQUIRED_ANALYSIS=VALID")
    print("I008_RUNTIME_ENFORCEMENT=PRESENT")
    print("I008_TESTS=PRESENT")
    print("I008_CONTRACT=VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
