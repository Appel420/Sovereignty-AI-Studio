"""Focused governance tests for scripts/run-local-ci.py."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "run-local-ci.py"
SPEC = importlib.util.spec_from_file_location("run_local_ci", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_mode_parser_accepts_local_hybrid_online() -> None:
    assert MODULE.parse_mode_from_name("coordination-unit-ci-local") == "local"
    assert MODULE.parse_mode_from_name("coordination-unit-ci-hybrid") == "hybrid"
    assert MODULE.parse_mode_from_name("coordination-unit-ci-online") == "online"


def test_mode_parser_rejects_implicit_or_legacy_modes() -> None:
    for name in ("coordination-unit-ci", "coordination-unit-ci-offline", "coordination-unit-ci-ghost"):
        try:
            MODULE.parse_mode_from_name(name)
        except ValueError:
            pass
        else:
            raise AssertionError(f"mode must fail closed: {name}")


def test_external_modes_require_explicit_operation_metadata() -> None:
    assert MODULE.validate_external_metadata(
        mode="hybrid", confirm_mode="", destination="", scope="", why=""
    ) == ["--confirm-mode hybrid", "--destination", "--scope", "--why"]

    assert MODULE.validate_external_metadata(
        mode="online",
        confirm_mode="online",
        destination="approved-destination",
        scope="coordination-validation",
        why="owner-approved validation",
    ) == []


def test_local_mode_requires_no_external_metadata() -> None:
    assert MODULE.validate_external_metadata(
        mode="local", confirm_mode="", destination="", scope="", why=""
    ) == []


def test_local_environment_disables_external_execution_defaults() -> None:
    env = MODULE.local_env()
    assert env["SG_NETWORK_MODE"] == "offline"
    assert env["SG_LOCAL_ONLY"] == "1"
    assert env["SG_EXTERNAL_FEEDS"] == "disabled"
    assert env["CLOUD_FIRST"] == "false"
    assert env["PIP_NO_INDEX"] == "1"
    assert env["npm_config_offline"] == "true"
    assert env["NO_PROXY"] == "*"
    assert env["no_proxy"] == "*"
    assert str(Path(MODULE.ROOT)) in env["PYTHONPATH"].split(":")


def test_build_stamp_contains_governance_metadata() -> None:
    stamp = MODULE.build_stamp(
        ci_name="coordination-unit-ci-local",
        mode="local",
        why="focused governance validation",
        action="local-validation",
        destination="",
        scope="coordination",
        started=datetime.now(timezone.utc),
        results=[{"suite": "coordination", "exit": 0, "tests": 3}],
        isolation="network-namespace",
    )

    assert stamp["ci_mode"] == "local"
    assert stamp["route"] == "device-offline"
    assert stamp["action"] == "local-validation"
    assert stamp["destination"] == ""
    assert stamp["scope"] == "coordination"
    assert stamp["why"] == "focused governance validation"
    assert stamp["status"] == "PASS"
    assert stamp["external_execution"] is False
    assert stamp["scar"]["event_type"] == "LOCAL_CI_COMPLETED"
    assert stamp["scar"]["event_class"] == "verification"
    assert stamp["scar"]["metadata"]["mode"] == "local"
    assert stamp["scar"]["metadata"]["network"] == "isolated"
    assert stamp["scar"]["metadata"]["package_install"] == "disabled"
    assert stamp["scar"]["metadata"]["provider_calls"] == "disabled"
    assert stamp["scar"]["metadata"]["external_execution"] is False


def test_build_stamp_fails_when_any_suite_fails() -> None:
    stamp = MODULE.build_stamp(
        ci_name="coordination-unit-ci-local",
        mode="local",
        why="negative governance test",
        action="local-validation",
        destination="",
        scope="coordination",
        started=datetime.now(timezone.utc),
        results=[{"suite": "coordination", "exit": 1, "tests": 3}],
        isolation="network-namespace",
    )

    assert stamp["status"] == "FAIL"
