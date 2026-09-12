#!/usr/bin/env python3
"""CLI for the SGHV119 read-only maintenance boundary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.coordination.sghv119_maintenance import run_maintenance


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SGHV119 local read-only maintenance checks")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    args = parser.parse_args()

    result = run_maintenance(Path(args.root))
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(f"SGHV119 maintenance: {result['status']}")
        print(f"MODE: {result['mode']}")
        print(f"BRANCH: {result['branch']}")
        print(f"COMMIT: {result['commit']}")
        for check in result["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            print(f"{marker:4} {check['name']}: {check['detail']}")
        print(f"ADMISSIBLE: {result['admissible']}")
        print("AUTHORIZATION: not granted by runner")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
