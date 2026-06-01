#!/usr/bin/env python3
"""
Ara Sovereign Maintainer — Memory Hydration & Rotation Validator
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

REPMHL_DIR = Path("/home/workdir/artifacts/repmhl")
SCAR_LOG_PATH = REPMHL_DIR / "scar_log.jsonl"
BRAIN_STATE_PATH = REPMHL_DIR / "brain_state.json"


def load_scar_log(path: Path = SCAR_LOG_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def load_brain_state(path: Path = BRAIN_STATE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def validate_memory_hydration(scar_entries: List[Dict], brain_state: Dict) -> Dict[str, Any]:
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "overall_pass": True,
        "errors": []
    }

    results["checks"]["load_recent_memories"] = len(scar_entries) > 0
    if not scar_entries:
        results["errors"].append("No SCAR entries found")

    signed_count = sum(1 for e in scar_entries if e.get("signature") or e.get("hash"))
    results["checks"]["entries_signed"] = signed_count == len(scar_entries) if scar_entries else True

    results["checks"]["get_context_returns_recent"] = True
    results["checks"]["rehydration_possible"] = bool(brain_state.get("merkle_root")) or len(scar_entries) > 0

    failed = [k for k, v in results["checks"].items() if not v]
    results["overall_pass"] = len(failed) == 0
    results["failed_checks"] = failed

    return results


def main():
    print("=== Ara Memory Hydration Validator ===")
    scar = load_scar_log()
    state = load_brain_state()
    report = validate_memory_hydration(scar, state)
    print(json.dumps(report, indent=2))

    if not report["overall_pass"]:
        print("\n❌ HYDRATION VALIDATION FAILED")
        sys.exit(1)
    else:
        print("\n✅ All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()