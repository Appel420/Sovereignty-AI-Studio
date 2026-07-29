#!/usr/bin/env python3
"""Report and validate canonical SGHv119 ownership boundaries."""
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
    "truncated_placeholder": r"trimmed for brevity",
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
            if count and name in {
                "hawking_definition",
                "bridge_singleton",
                "duplicate_ws_manager",
                "legacy_local_block",
                "truncated_placeholder",
            } and path.name == "SGHv119.html":
                failed = True
    if failed:
        print("SGHv119 cleanup required: canonical dashboard still owns duplicate or truncated runtime code", file=sys.stderr)
        return 1
    print("dashboard ownership report passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
