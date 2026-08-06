"""Tests for the zero-tolerance security policy scanner.

TEST HARNESS ONLY. These tests prove scanner behavior; they are not security
attestation and do not certify any runtime or hardware capability.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.security_policy_scan import load_policy, scan, scan_file, validate_policy


def policy() -> dict:
    return {
        "policy_id": "test-policy",
        "enforcement": {"mode": "deny", "fail_ci": True},
        "protected_paths": ["security/"],
        "forbidden_patterns": [
            {
                "category": "test",
                "patterns": ["is_valid: true"],
                "rule": "test claims are forbidden",
            }
        ],
    }


def test_policy_requires_deny_and_fail_ci() -> None:
    validate_policy(policy())
    invalid = policy()
    invalid["enforcement"]["mode"] = "allow"
    with pytest.raises(ValueError, match="deny mode"):
        validate_policy(invalid)


def test_scan_file_detects_forbidden_pattern(tmp_path: Path) -> None:
    path = tmp_path / "security.rs"
    path.write_text('const CLAIM: &str = "is_valid: true";', encoding="utf-8")
    assert scan_file(path, ["is_valid: true"]) == ["is_valid: true"]


def test_scan_ignores_unprotected_paths(tmp_path: Path) -> None:
    (tmp_path / "security").mkdir()
    (tmp_path / "security" / "safe.txt").write_text("safe", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("is_valid: true", encoding="utf-8")
    findings = scan(tmp_path, policy())
    assert findings == []


def test_scan_reports_protected_violation(tmp_path: Path) -> None:
    secure = tmp_path / "security"
    secure.mkdir()
    (secure / "bad.txt").write_text("is_valid: true", encoding="utf-8")
    findings = scan(tmp_path, policy())
    assert len(findings) == 1
    assert findings[0].category == "test"


def test_policy_file_is_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy()), encoding="utf-8")
    loaded = load_policy(path)
    validate_policy(loaded)
