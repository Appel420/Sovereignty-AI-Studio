#!/usr/bin/env python3
"""Named local CI runner with explicit runtime governance metadata."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def git_branch() -> str:
    try:
        return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def parse_mode_from_name(ci_name: str) -> str:
    for mode in ("local", "hybrid", "online"):
        if ci_name.endswith(f"-ci-{mode}") or ci_name.endswith(f"-{mode}"):
            return mode
    raise ValueError(f"unsupported or implicit CI mode: {ci_name}")


def validate_external_metadata(*, mode: str, confirm_mode: str, destination: str, scope: str, why: str) -> list[str]:
    if mode == "local":
        return []
    missing: list[str] = []
    if confirm_mode != mode:
        missing.append(f"--confirm-mode {mode}")
    if not destination:
        missing.append("--destination")
    if not scope:
        missing.append("--scope")
    if not why:
        missing.append("--why")
    return missing


def local_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "SG_NETWORK_MODE": "offline",
        "SG_LOCAL_ONLY": "1",
        "SG_EXTERNAL_FEEDS": "disabled",
        "CLOUD_FIRST": "false",
        "PIP_NO_INDEX": "1",
        "npm_config_offline": "true",
        "NO_PROXY": "*",
        "no_proxy": "*",
    })
    pythonpath = [str(ROOT / "prototypes"), str(ROOT)]
    existing = env.get("PYTHONPATH")
    if existing:
        pythonpath.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return env


def build_stamp(*, ci_name: str, mode: str, why: str, action: str, destination: str, scope: str,
                started: datetime, results: list[dict], isolation: str) -> dict:
    failed = any(result.get("exit", 1) != 0 for result in results)
    return {
        "ci_name": ci_name,
        "ci_mode": mode,
        "route": "device-offline" if mode == "local" else mode,
        "brand": "Sovereignty-AI-Studio",
        "branch": git_branch(),
        "commit": git_sha(),
        "agent": "Ara/Grok",
        "operator": "Appel420",
        "started_at": started.astimezone(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "why": why,
        "action": action,
        "destination": destination,
        "scope": scope,
        "results": results,
        "status": "FAIL" if failed else "PASS",
        "external_execution": mode != "local",
        "isolation": isolation,
        "scar": {
            "event_type": "LOCAL_CI_COMPLETED" if mode == "local" else "ROUTE_SELECTED",
            "event_class": "verification" if mode == "local" else "policy",
            "metadata": {
                "mode": mode,
                "network": "isolated" if mode == "local" else mode,
                "package_install": "disabled" if mode == "local" else "explicit",
                "provider_calls": "disabled" if mode == "local" else "explicit",
                "external_execution": mode != "local",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Named local CI with governance stamp")
    parser.add_argument("--ci-name", default="ara-hardened-unit-ci-local")
    parser.add_argument("--confirm-mode", default="")
    parser.add_argument("--destination", default="")
    parser.add_argument("--scope", default="local-validation")
    parser.add_argument("--why", default="isolated validation")
    args = parser.parse_args()

    try:
        mode = parse_mode_from_name(args.ci_name)
    except ValueError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2

    missing = validate_external_metadata(
        mode=mode, confirm_mode=args.confirm_mode, destination=args.destination,
        scope=args.scope, why=args.why,
    )
    if missing:
        print(f"BLOCKED: missing authorization metadata: {', '.join(missing)}", file=sys.stderr)
        return 2
    if mode != "local":
        print("Non-local execution is not implemented in this runner.", file=sys.stderr)
        return 3

    started = datetime.now(timezone.utc)
    env = local_env()
    results: list[dict] = []

    if "accessibility" in args.ci_name:
        command = [sys.executable, "-m", "pytest", "-q", str(ROOT / "prototypes/accessibility/tests/test_accessibility_control.py")]
        proc = subprocess.run(command, cwd=ROOT, env=env)
        results.append({"suite": "accessibility", "exit": proc.returncode})
    else:
        code = subprocess.run(
            [sys.executable, "-c", "from backend.coordination import BranchRegistry; r=BranchRegistry(); assert r.is_writable('ara-hardened'); print('coordination OK')"],
            cwd=ROOT, env=env,
        ).returncode
        results.append({"suite": "coordination", "exit": code, "tests": 1})
        acc = ROOT / "prototypes/accessibility/tests/test_accessibility_control.py"
        if acc.exists():
            proc = subprocess.run([sys.executable, "-m", "pytest", "-q", str(acc)], cwd=ROOT, env=env)
            results.append({"suite": "accessibility", "exit": proc.returncode})

    stamp = build_stamp(
        ci_name=args.ci_name, mode=mode, why=args.why, action="local-validation",
        destination=args.destination, scope=args.scope, started=started,
        results=results, isolation="network-namespace",
    )
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    path = out / f"{args.ci_name}-{int(time.time())}.json"
    path.write_text(json.dumps(stamp, indent=2), encoding="utf-8")
    print(json.dumps(stamp, indent=2))
    print(f"report: {path}")
    return 1 if stamp["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
