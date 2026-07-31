"""Read-only status for the local dashboard build surface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _exists(relative: str) -> bool:
    return (ROOT / relative).is_file()


def local_status() -> dict[str, Any]:
    """Return local-only contract and Apple M4 documentation availability."""
    oauth_policy = ROOT / "config" / "local-oauth-policy.json"
    policy: dict[str, Any] = {}
    if oauth_policy.is_file():
        try:
            policy = json.loads(oauth_policy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            policy = {}

    m4_doc = ROOT / "docs" / "apple_m4_neural.md"
    return {
        "mode": "offline",
        "network_access": False,
        "external_oauth": policy.get("external_oauth", "disabled"),
        "oauth_policy": _exists("config/local-oauth-policy.json"),
        "oauth_generator": _exists("scripts/oauth_local_generator.py"),
        "local_state_validator": _exists("scripts/validate-local-state.sh"),
        "local_ci": _exists("scripts/local-ci.sh"),
        "m4_neural": {
            "available": m4_doc.is_file(),
            "path": "docs/apple_m4_neural.md",
            "tops": 38,
            "memory": "unified",
            "href": "docs/apple_m4_neural.md",
        },
    }
