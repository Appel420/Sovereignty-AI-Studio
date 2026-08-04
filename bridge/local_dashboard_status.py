#!/usr/bin/env python3
"""Read-only status for the local dashboard build surface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _exists(relative: str) -> bool:
    return (ROOT / relative).is_file()


def local_status() -> dict[str, Any]:
    oauth_policy_path = ROOT / "config" / "local-oauth-policy.json"
    policy: dict[str, Any] = {}
    if oauth_policy_path.is_file():
        try:
            policy = json.loads(oauth_policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            policy = {}

    try:
        from scripts.audit_external_integrations import inventory
        external = inventory()
    except Exception as exc:  # pragma: no cover - status must remain readable
        external = {
            "mode": "offline",
            "network_access": False,
            "inventory_error": str(exc),
            "source": "local-read-only-inventory",
        }

    return {
        "mode": "offline",
        "network_access": False,
        "external_oauth": policy.get("external_oauth", "disabled"),
        "oauth_policy": _exists("config/local-oauth-policy.json"),
        "oauth_generator": _exists("scripts/oauth_local_generator.py"),
        "local_state_validator": _exists("scripts/validate-local-state.sh"),
        "local_ci": _exists("scripts/local-ci.sh"),
        "external_integrations": external,
    }
