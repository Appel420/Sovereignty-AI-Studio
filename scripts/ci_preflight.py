#!/usr/bin/env python3
"""Read-only CI preflight gate.

Produces an owner-visible review/statistics report before a CI execution path
is allowed to continue. It does not execute builds, workflows, network calls,
or repository mutations.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODES = {"local", "hybrid", "online"}
DECISIONS = {"PENDING", "APPROVED", "DENIED", "CANCELLED"}


def run_git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def stats() -> dict:
    status = run_git("status", "--short")
    diff = run_git("diff", "--shortstat")
    branch = run_git("branch", "--show-current")
    commit = run_git("rev-parse", "HEAD")
    return {
        "branch": branch or "DETACHED",
        "commit": commit,
        "worktree_clean": not bool(status),
        "changed_files": len([line for line in status.splitlines() if line]),
        "diff_stat": diff,
    }


def evaluate(mode: str, decision: str, approval_id: str) -> tuple[str, list[str]]:
    errors: list[str] = []
    if mode not in MODES:
        errors.append(f"unsupported mode: {mode}")
    if decision not in DECISIONS:
        errors.append(f"unsupported decision: {decision}")
    if mode in {"hybrid", "online"}:
        if decision != "APPROVED":
            errors.append("external execution requires explicit APPROVED owner decision")
        if not approval_id:
            errors.append("external execution requires an approval id")
    if decision in {"DENIED", "CANCELLED"}:
        return "DENY", errors
    if errors:
        return "BLOCKED", errors
    return "ALLOW", []


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only CI preflight gate")
    parser.add_argument("--mode", choices=sorted(MODES), default="local")
    parser.add_argument("--decision", choices=sorted(DECISIONS), default="PENDING")
    parser.add_argument("--approval-id", default="")
    parser.add_argument("--purpose", default="CI validation")
    args = parser.parse_args()

    try:
        repository = stats()
    except subprocess.CalledProcessError as exc:
        print(f"BLOCKED: unable to inspect repository: {exc.output.strip()}", file=sys.stderr)
        return 2

    decision, errors = evaluate(args.mode, args.decision, args.approval_id)
    report = {
        "schema": "sovereignty-ci-preflight/v1",
        "event": "CI_PREFLIGHT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "operator": "Appel420",
        "purpose": args.purpose,
        "mode": args.mode,
        "owner_decision": args.decision,
        "approval_id": args.approval_id or None,
        "repository": repository,
        "result": decision,
        "errors": errors,
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    path = out / "ci-preflight.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"report: {path}")
    return 0 if decision == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
