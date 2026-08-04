#!/usr/bin/env python3
"""Run coordination checks on this device with enforced offline isolation.

This is not GitHub Actions. It installs nothing, dispatches no hosted runner,
and runs only repository-local coordination tests. On Linux, local mode re-execs
inside an unshared network namespace by default; if that isolation is unavailable,
the run fails before tests execute.

Usage:
  python3 scripts/run-local-ci.py --ci-name coordination-unit-ci-local
  python3 scripts/run-local-ci.py --ci-name coordination-unit-ci-local \
      --offline-enforcement best-effort
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COORDINATION_TESTS = ROOT / "backend" / "coordination"
LOCAL_ENV = {
    "SG_NETWORK_MODE": "offline",
    "SG_LOCAL_ONLY": "1",
    "SG_EXTERNAL_FEEDS": "disabled",
    "CLOUD_FIRST": "false",
    "PIP_NO_INDEX": "1",
    "PIP_NO_INPUT": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "npm_config_offline": "true",
    "npm_config_audit": "false",
    "npm_config_fund": "false",
    "NO_PROXY": "*",
    "no_proxy": "*",
}


def parse_mode_from_name(ci_name: str) -> str:
    """Return the explicit mode suffix; names without one fail closed."""
    for mode in ("local", "hybrid", "online"):
        if ci_name.endswith(f"-ci-{mode}") or ci_name.endswith(f"-{mode}"):
            return mode
    raise ValueError("ci-name must end with -ci-local, -ci-hybrid, or -ci-online")


def command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, cwd=ROOT, text=True, env=local_env()).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def local_env() -> dict[str, str]:
    """Return the environment inherited by every local test subprocess."""
    environment = dict(os.environ)
    environment.update(LOCAL_ENV)
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(ROOT), environment.get("PYTHONPATH", "")) if part
    )
    return environment


def coordination_test_files() -> list[Path]:
    return sorted(COORDINATION_TESTS.glob("test_*.py"))


def reexec_in_network_namespace(args: argparse.Namespace) -> int | None:
    """Re-exec under Linux network isolation, or fail before any test starts."""
    if os.environ.get("SG_LOCAL_CI_NETNS") == "1":
        return None
    if args.offline_enforcement == "none":
        return None
    if sys.platform != "linux":
        if args.offline_enforcement == "required":
            print("BLOCKED: required offline isolation needs Linux network namespaces", file=sys.stderr)
            return 2
        return None

    unshare = shutil.which("unshare")
    if unshare is None:
        if args.offline_enforcement == "required":
            print("BLOCKED: required offline isolation needs the local 'unshare' command", file=sys.stderr)
            return 2
        return None

    command = [
        unshare,
        "--user",
        "--map-root-user",
        "--net",
        "--mount-proc",
        "env",
        "SG_LOCAL_CI_NETNS=1",
        *[f"{key}={value}" for key, value in LOCAL_ENV.items()],
        sys.executable,
        str(Path(__file__).resolve()),
        *sys.argv[1:],
    ]
    completed = subprocess.run(command, cwd=ROOT, env=local_env())
    if completed.returncode != 0 and args.offline_enforcement == "required":
        print(
            "BLOCKED: the host refused the network namespace; no tests were run outside it. "
            "Use a Linux host with unprivileged user namespaces enabled.",
            file=sys.stderr,
        )
    return completed.returncode


def build_stamp(
    *,
    ci_name: str,
    why: str,
    started: datetime,
    results: list[dict[str, Any]],
    isolation: str,
) -> dict[str, Any]:
    failed = any(result["exit"] != 0 for result in results)
    completed = datetime.now(timezone.utc)
    return {
        "ci_name": ci_name,
        "ci_mode": "local",
        "route": "device-offline",
        "branch": command_output(["git", "branch", "--show-current"]),
        "commit": command_output(["git", "rev-parse", "HEAD"]),
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "why": why,
        "status": "FAIL" if failed else "PASS",
        "results": results,
        "scar": {
            "event_type": "LOCAL_CI_COMPLETED",
            "event_class": "verification",
            "metadata": {
                "mode": "local",
                "network": "isolated" if isolation == "network-namespace" else "not-enforced",
                "package_install": "disabled",
                "provider_calls": "disabled",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Device-local, offline coordination CI")
    parser.add_argument("--ci-name", default="coordination-unit-ci-local")
    parser.add_argument("--why", default="offline coordination validation")
    parser.add_argument(
        "--offline-enforcement",
        choices=("required", "best-effort", "none"),
        default="required",
        help="required is the default and refuses to run outside a Linux network namespace",
    )
    args = parser.parse_args()

    try:
        mode = parse_mode_from_name(args.ci_name)
    except ValueError as error:
        parser.error(str(error))
    if mode != "local":
        print("BLOCKED: this runner implements device-local mode only", file=sys.stderr)
        return 2

    isolated = reexec_in_network_namespace(args)
    if isolated is not None:
        return isolated

    if importlib.util.find_spec("pytest") is None:
        print("BLOCKED: pytest is not installed locally; this runner never installs packages", file=sys.stderr)
        return 2

    test_files = coordination_test_files()
    if not test_files:
        print("BLOCKED: no backend/coordination/test_*.py files found", file=sys.stderr)
        return 2

    started = datetime.now(timezone.utc)
    command = [sys.executable, "-m", "pytest", "-q", *map(str, test_files)]
    print("=" * 60)
    print(f"CI:     {args.ci_name}")
    print("MODE:   LOCAL (device-only)")
    print("NETWORK: isolated network namespace")
    print("PACKAGES: existing local environment only")
    print("SUITE:  backend/coordination/test_*.py")
    print("=" * 60)
    process = subprocess.run(command, cwd=ROOT, env=local_env())
    results = [{"suite": "coordination", "exit": process.returncode, "tests": len(test_files)}]
    stamp = build_stamp(
        ci_name=args.ci_name,
        why=args.why,
        started=started,
        results=results,
        isolation="network-namespace",
    )

    reports = ROOT / "reports"
    reports.mkdir(mode=0o700, exist_ok=True)
    report_path = reports / f"{args.ci_name}-{int(time.time())}.json"
    report_path.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stamp, indent=2))
    print(f"report: {report_path}")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
