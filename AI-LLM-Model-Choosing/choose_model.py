#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ai_core.model_selection import known_models, select_model


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Select and route AI model ids")
    parser.add_argument("--list", action="store_true", help="List known model ids")
    parser.add_argument("--model", help="Model identifier (e.g. qwen-7b, grok-4-3)")
    parser.add_argument("--task", default="chat", choices=["chat", "judge"])
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(known_models()))
        return 0

    if not args.model:
        parser.error("--model is required unless --list is used")

    selection = select_model(args.model, task=args.task)
    print(json.dumps(selection.__dict__, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
