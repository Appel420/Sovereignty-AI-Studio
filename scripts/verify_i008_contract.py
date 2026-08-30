#!/usr/bin/env python3
"""Executable repository gate for frozen I-008 deterministic transparency."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "option-set-with-risk-reward.schema.json"
MODULE_PATH = ROOT / "backend" / "coordination" / "i008_transparency.py"
TEST_PATH = ROOT / "tests" / "test_i008_transparency.py"


def main() -> int:
    if not SCHEMA_PATH.is_file() or not MODULE_PATH.is_file() or not TEST_PATH.is_file():
        print("FAIL: I-008 canonical artifacts are incomplete", file=sys.stderr)
        return 1
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        required = set(schema["properties"]["options"]["items"]["required"])
        expected = {"id", "label", "pros", "cons", "risks", "rewards"}
        if not expected.issubset(required):
            raise ValueError(f"missing option fields: {sorted(expected - required)}")

        sys.path.insert(0, str(ROOT))
        from backend.coordination.i008_transparency import (  # pylint: disable=import-outside-toplevel
            I008Violation,
            execute_authorized_action,
            declare_action,
        )

        option_set = {"options": [{
            "id": "verification",
            "label": "Run verification",
            "pros": ["Produces evidence"],
            "cons": ["Consumes CI time"],
            "risks": ["Verification can fail"],
            "rewards": ["Validated repository state"],
        }]}
        events = []
        declaration = declare_action(
            decision_class="ALLOW",
            side_effects=["test execution"],
            data_egress=["CI metadata only"],
            persistence=["SCAR evidence"],
            provider_or_technology=["GitHub-hosted runner"],
        )
        result = execute_authorized_action(
            declaration=declaration,
            option_set=option_set,
            option_schema=schema,
            owner_decision="ALLOW",
            pre_action_evidence=events.append,
            incident=events.append,
            owner_alert=events.append,
            action=lambda: "executed",
            post_action_receipt=events.append,
        )
        if result != "executed" or [e["event"] for e in events] != ["pre_action_declaration", "post_action_receipt"]:
            raise AssertionError("I-008 gate sequence did not execute in required order")

        executed = []
        try:
            execute_authorized_action(
                declaration=None,
                option_set=option_set,
                option_schema=schema,
                owner_decision="ALLOW",
                pre_action_evidence=events.append,
                incident=events.append,
                owner_alert=events.append,
                action=lambda: executed.append(True),
                post_action_receipt=events.append,
            )
        except I008Violation:
            pass
        else:
            raise AssertionError("missing declaration did not fail closed")
        if executed:
            raise AssertionError("blocked I-008 action executed")
    except Exception as exc:
        print(f"FAIL: I-008 executable verification failed: {exc}", file=sys.stderr)
        return 1

    print("I008_SCHEMA=VALID")
    print("I008_REQUIRED_ANALYSIS=VALID")
    print("I008_RUNTIME_SEQUENCE=VERIFIED")
    print("I008_FAIL_CLOSED=VERIFIED")
    print("I008_TESTS=PRESENT")
    print("I008_CONTRACT=VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
