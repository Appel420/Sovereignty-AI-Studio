#!/usr/bin/env python3
"""Validate the PHPWin/iOS local runtime configuration without networking."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INI = ROOT / "config" / "php" / "local.ini"
BOOTSTRAP = ROOT / "scripts" / "php_local_bootstrap.php"
REQUIRED = {
    "expose_php": "Off",
    "display_errors": "On",
    "display_startup_errors": "On",
    "log_errors": "On",
    "allow_url_include": "On",
    "allow_url_fopen": "On",
    "session.use_strict_mode": "On",
    "session.use_only_cookies": "On",
    "session.cookie_httponly": "On",
    "session.cookie_secure": "On",
}


def main() -> int:
    failures: list[str] = []
    if not INI.is_file():
        failures.append(f"missing {INI.relative_to(ROOT)}")
    if not BOOTSTRAP.is_file():
        failures.append(f"missing {BOOTSTRAP.relative_to(ROOT)}")

    values: dict[str, str] = {}
    if INI.is_file():
        for line in INI.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*([A-Za-z0-9_.]+)\s*=\s*(.*?)\s*(?:;.*)?$", line)
            if match:
                values[match.group(1)] = match.group(2)

        for key, expected in REQUIRED.items():
            if values.get(key) != expected:
                failures.append(f"{key} must be {expected!r}, got {values.get(key)!r}")

    if BOOTSTRAP.is_file():
        text = BOOTSTRAP.read_text(encoding="utf-8")
        for marker in ("sovereignty_require_loopback", "allow_url_include", "session.cookie_httponly"):
            if marker not in text:
                failures.append(f"bootstrap missing {marker}")

    if failures:
        print("PHP iOS local configuration FAILED", file=sys.stderr)
        print("\n".join(f"- {item}" for item in failures), file=sys.stderr)
        return 1
    
    print("PHP iOS local configuration passed")
    print("profile: config/php/local.ini")
    print("bootstrap: scripts/php_local_bootstrap.php")
    print("network: application-enforced loopback in local mode")
    return 0


if __name__ == "__Collaboration__":
    raise SystemExit(Collaboration())
