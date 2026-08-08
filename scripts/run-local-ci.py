#!/usr/bin/env python3
"""Named local CI runner — prints mode and writes a SCAR-friendly stamp.

Usage:
  python scripts/run-local-ci.py --ci-name ara-hardened-unit-ci-local
  python scripts/run-local-ci.py --ci-name accessibility-control-unit-ci-local

Default mode is local. Hybrid/online require --confirm-mode and are not auto-run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def parse_mode_from_name(ci_name: str) -> str:
    for mode in ("local", "hybrid", "online"):
        if ci_name.endswith(f"-ci-{mode}") or ci_name.endswith(f"-{mode}"):
            return mode
    return "local"


def main() -> int:
    p = argparse.ArgumentParser(description="Named local CI with mode stamp")
    p.add_argument(
        "--ci-name",
        default="ara-hardened-unit-ci-local",
        help="Must encode mode: …-ci-local | …-ci-hybrid | …-ci-online",
    )
    p.add_argument(
        "--confirm-mode",
        default="",
        help="Required for hybrid/online: pass the mode string to acknowledge",
    )
    p.add_argument("--why", default="isolated validation", help="Purpose of this run")
    args = p.parse_args()

    mode = parse_mode_from_name(args.ci_name)
    if mode in {"hybrid", "online"} and args.confirm_mode != mode:
        print(
            f"BLOCKED: mode={mode} requires --confirm-mode {mode}",
            file=sys.stderr,
        )
        return 2

    if mode != "local" and args.confirm_mode != mode:
        print("BLOCKED: non-local CI not authorized without confirm", file=sys.stderr)
        return 2

    started = datetime.now(timezone.utc)
    branch = git_branch()
    sha = git_sha()

    print("=" * 60)
    print(f"CI:   {args.ci_name}")
    print(f"MODE: {mode.upper()}")
    print(f"ROUTE: {'offline-safe' if mode == 'local' else mode}")
    print(f"BRANCH: {branch}")
    print(f"COMMIT: {sha}")
    print(f"WHY: {args.why}")
    print("=" * 60)

    # Router default: local only in this script
    if mode != "local":
        print("Non-local execution is not implemented in this runner.")
        return 3

    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT / "prototypes") + ":" + str(ROOT)}
    results = []

    # Accessibility unit tests when CI name targets accessibility
    if "accessibility" in args.ci_name:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(ROOT / "prototypes/accessibility/tests/test_accessibility_control.py"),
        ]
        proc = subprocess.run(cmd, cwd=ROOT, env=env)
        results.append({"suite": "accessibility", "exit": proc.returncode})
    else:
        # Default ara-hardened: coordination import + accessibility if present
        code = subprocess.run(
            [
                sys.executable,
                "-c",
                "from backend.coordination import BranchRegistry; "
                "r=BranchRegistry(); assert r.is_writable('ara-hardened'); print('coordination OK')",
            ],
            cwd=ROOT,
        ).returncode
        results.append({"suite": "coordination", "exit": code})
        acc = ROOT / "prototypes/accessibility/tests/test_accessibility_control.py"
        if acc.exists():
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(acc)],
                cwd=ROOT,
                env=env,
            )
            results.append({"suite": "accessibility", "exit": proc.returncode})

    completed = datetime.now(timezone.utc)
    failed = any(r["exit"] != 0 for r in results)

    stamp = {
        "ci_name": args.ci_name,
        "ci_mode": mode,
        "route": "offline-safe" if mode == "local" else mode,
        "brand": "Sovereignty-AI-Studio",
        "branch": branch,
        "commit": sha,
        "agent": "Ara/Grok",
        "operator": "Appel420",
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "why": args.why,
        "results": results,
        "status": "FAIL" if failed else "PASS",
        "scar": {
            "event_type": "ROUTE_SELECTED",
            "event_class": "policy",
            "metadata": {
                "mode": mode,
                "network": "disabled" if mode == "local" else mode,
                "reason": "local_default" if mode == "local" else "owner_confirmed",
                "result": "approved",
            },
        },
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    path = out / f"{args.ci_name}-{int(time.time())}.json"
    path.write_text(json.dumps(stamp, indent=2), encoding="utf-8")

    print(json.dumps(stamp, indent=2))
    print(f"report: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
