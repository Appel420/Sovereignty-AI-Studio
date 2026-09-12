#!/usr/bin/env python3
"""Local notification and owner-decision CLI for governed operations."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from local_governance.approvals import ApprovalStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Local approval notifications")
    parser.add_argument(
        "--store",
        type=Path,
        default=Path(os.environ.get("SG_APPROVALS", "state/approvals.jsonl")),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    request = sub.add_parser("request")
    request.add_argument("kind", choices=("PROCESS", "DEPLOYMENT", "COMMIT"))
    request.add_argument("subject")
    request.add_argument("summary")
    request.add_argument("--requested-by", default="local-agent")
    request.add_argument("--payload", default="{}")

    listing = sub.add_parser("list")
    listing.add_argument("--state")
    listing.add_argument("--kind")

    decide = sub.add_parser("decide")
    decide.add_argument("approval_id")
    decide.add_argument(
        "decision",
        choices=("APPROVED", "DENIED", "EXPIRED", "CANCELLED", "HELD"),
    )
    decide.add_argument("--owner", required=True)

    args = parser.parse_args()
    store = ApprovalStore(args.store)
    if args.command == "request":
        result = store.request(
            kind=args.kind,
            subject=args.subject,
            summary=args.summary,
            requested_by=args.requested_by,
            payload=json.loads(args.payload),
        )
    elif args.command == "list":
        result = store.list(state=args.state, kind=args.kind)
    else:
        result = store.decide(args.approval_id, args.decision, args.owner)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
