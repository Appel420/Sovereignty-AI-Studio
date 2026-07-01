#!/usr/bin/env python3
"""SGHV119 offline inventory report.

Local report-only helper. It reads repository files and PLATFORM.json, then writes
an offline inventory summary for cave-mode cleanup planning. It performs no
network calls and makes no source changes.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "automation" / "reports"
PLATFORM_PATH = ROOT / "PLATFORM.json"
IGNORE_NAMES = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "automation"}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def skip(path: Path) -> bool:
    return any(part in IGNORE_NAMES for part in path.parts)


def read_platform() -> Dict[str, Any]:
    if not PLATFORM_PATH.exists():
        return {}
    try:
        return json.loads(PLATFORM_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}


def files() -> List[Path]:
    return sorted([p for p in ROOT.rglob("*") if p.is_file() and not skip(p)], key=lambda p: rel(p))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(131072), b""):
            h.update(block)
    return h.hexdigest()


def starts(value: str, prefixes: List[str]) -> bool:
    return any(value == prefix.rstrip("/") or value.startswith(prefix) for prefix in prefixes)


def classify(path: Path, platform: Dict[str, Any]) -> str:
    name = rel(path)
    if starts(name, platform.get("archive_candidate_roots", [])):
        return "archive_candidate"
    if starts(name, platform.get("allowed_active_roots", [])):
        return "active_or_support"
    return "needs_owner"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    platform = read_platform()
    all_files = files()
    inventory = []
    duplicate_buckets: Dict[str, List[str]] = defaultdict(list)
    summary = {
        "mode": "offline_report_only",
        "platform": platform.get("platform", "unknown"),
        "entrypoint": platform.get("entrypoint"),
        "file_count": len(all_files),
        "classifications": {},
        "duplicate_groups": 0,
        "reports": {
            "inventory": "automation/reports/offline-inventory.json",
            "summary": "automation/reports/offline-inventory-summary.json"
        }
    }

    for path in all_files:
        item = {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "classification": classify(path, platform),
            "sha256": digest(path)
        }
        inventory.append(item)
        duplicate_buckets[item["sha256"]].append(item["path"])
        summary["classifications"][item["classification"]] = summary["classifications"].get(item["classification"], 0) + 1

    duplicates = {key: value for key, value in duplicate_buckets.items() if len(value) > 1}
    summary["duplicate_groups"] = len(duplicates)

    (REPORT_DIR / "offline-inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORT_DIR / "offline-duplicates.json").write_text(json.dumps(duplicates, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORT_DIR / "offline-inventory-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
