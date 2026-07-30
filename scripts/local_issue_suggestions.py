#!/usr/bin/env python3
"""Local CLI for observing and deciding deduplicated issue suggestions."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from local_governance.issue_suggestions import IssueSuggestionStore


def default_path() -> Path:
    return Path(os.environ.get("SG_ISSUE_SUGGESTIONS", "state/issue-suggestions.jsonl"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage device-local issue suggestions")
    parser.add_argument("--store", type=Path, default=default_path())
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--state")

    decide_parser = subparsers.add_parser("decide")
    decide_parser.add_argument("suggestion_id")
    decide_parser.add_argument("decision", choices=("ACCEPTED", "DECLINED", "DEFERRED", "RESOLVED"))

    args = parser.parse_args()
    store = IssueSuggestionStore(args.store)
    if args.command == "list":
        print(json.dumps(store.list(args.state), indent=2, sort_keys=True))
    else:
        print(json.dumps(store.decide(args.suggestion_id, args.decision), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
