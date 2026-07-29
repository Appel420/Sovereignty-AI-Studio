#!/usr/bin/env python3
"""Report duplicate runtime ownership markers without modifying dashboard files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (ROOT / "SGHv119.html", ROOT / "7-14-SGHV119.html")
PATTERNS = {
    "hawking_definition": r"SovereignHawkingChannel\s*=|SovereignHawkingChannel\s*\(",
    "bridge_singleton": r"_SG_BRIDGE_STATUS\s*=|BRIDGE STATUS SINGLETON",
    "bridge_fetch_fallback": r"/error_ping|/chat",
    "duplicate_ws_manager": r"new\s+WebSocket\s*\(|WebSocket\s*=",
    "legacy_local_block": r"Blocked in local/offline mode",
}


def main() -> int:
    failed = False
    for path in TARGETS:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        print(f"{path.relative_to(ROOT)}:")
        for name, pattern in PATTERNS.items():
            count = len(re.findall(pattern, source, flags=re.IGNORECASE))
            print(f"  {name}: {count}")
            if name == "legacy_local_block" and count:
                failed = True
    if failed:
        print("dashboard cleanup required: local mode still blocks all loopback bridge traffic", file=sys.stderr)
        return 1
    print("dashboard duplicate report completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
