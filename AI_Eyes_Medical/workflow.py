#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import sys


def _require_medicalai():
    try:
        import medicalai  # type: ignore[import]  # noqa: F401
    except ImportError as exc:  # noqa: PERF203
        raise SystemExit(
            "Missing optional dependency: medicalai\n"
            "Install with: python3 -m pip install medicalai\n"
            "Then re-run this script."
        ) from exc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Sample medical AI workflow (train/eval/explain)"
    )
    parser.add_argument("--data", type=pathlib.Path, default=pathlib.Path("data"))
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("artifacts"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument(
        "--step",
        choices=["all", "prepare", "train", "eval", "explain"],
        default="all",
        help="Which step(s) to run",
    )
    args = parser.parse_args(argv)

    # This is a sample: only enforce dependency when doing actual work.
    if args.step != "prepare":
        _require_medicalai()

    args.output.mkdir(parents=True, exist_ok=True)

    if args.step in ("all", "prepare"):
        print(f"[prepare] dataset_dir={args.data} (sample stub)")

    if args.step in ("all", "train"):
        print(f"[train] epochs={args.epochs} output_dir={args.output} (sample stub)")

    if args.step in ("all", "eval"):
        print(f"[eval] output_dir={args.output} (sample stub)")

    if args.step in ("all", "explain"):
        print(f"[explain] output_dir={args.output} (sample stub)")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

