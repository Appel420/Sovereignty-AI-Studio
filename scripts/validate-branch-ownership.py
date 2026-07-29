#!/usr/bin/env python3
"""Validate local branch/scope ownership without modifying the repository."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from backend.coordination import BranchRegistry, DevAssistRouter


def current_branch(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", help="Branch to validate; defaults to the current Git branch")
    parser.add_argument("--scope", action="append", default=[], help="Requested owned scope")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    branch = args.branch or current_branch(root)
    registry = BranchRegistry()
    owner = registry.get(branch)
    payload: dict[str, object] = {
        "branch": branch,
        "scope": args.scope,
        "valid": False,
        "reason": None,
    }
    if branch in {"", "HEAD"}:
        payload["reason"] = "detached or unknown branch"
    elif owner is None:
        payload["reason"] = "branch is not registered for agent coordination"
    elif not owner.allows(args.scope):
        payload["reason"] = f"scope is not owned by {owner.owner}"
    else:
        payload.update({"valid": True, "owner": owner.owner})

    if args.as_json:
        print(json.dumps(payload, sort_keys=True))
    else:
        status = "PASS" if payload["valid"] else "FAIL"
        print(f"{status}: {json.dumps(payload, sort_keys=True)}")
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
