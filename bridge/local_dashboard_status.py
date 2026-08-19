"""Read-only status for the local dashboard build surface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEVASSIST_STATUS_URL = "http://127.0.0.1:9899/api/devassist/status"


def _exists(relative: str) -> bool:
    return (ROOT / relative).is_file()


def _loopback_status(url: str = DEVASSIST_STATUS_URL) -> dict[str, Any]:
    if not url.startswith(("http://127.0.0.1:", "http://localhost:", "http://[::1]:")):
        return {"state": "UNAVAILABLE", "reason": "non-loopback endpoint rejected", "url": url}
    try:
        request = Request(url, headers={"Cache-Control": "no-store"})
        with urlopen(request, timeout=1.5) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("bridge status is not an object")
        return payload
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return {"state": "UNAVAILABLE", "reason": str(exc), "url": url}


def local_status() -> dict[str, Any]:
    policy_path = ROOT / "config" / "local-oauth-policy.json"
    policy: dict[str, Any] = {}
    if policy_path.is_file():
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    try:
        from scripts.audit_external_integrations import inventory
        external = inventory()
    except Exception as exc:  # pragma: no cover
        external = {"mode": "offline", "network_access": False, "inventory_error": str(exc)}

    devassist = _loopback_status()
    return {
        "mode": "offline",
        "network_access": False,
        "external_oauth": policy.get("external_oauth", "disabled"),
        "oauth_policy": _exists("config/local-oauth-policy.json"),
        "oauth_generator": _exists("scripts/oauth_local_generator.py"),
        "local_state_validator": _exists("scripts/validate-local-state.sh"),
        "local_ci": _exists("scripts/local-ci.sh"),
        "m4_neural": {
            "tops": 38,
            "memory": "unified",
            "path": "docs/apple_m4_neural.md",
        },
        "phpwin": {"state": "RUNNING", "source": "dashboard-process"},
        "node_bridge": {
            "state": "RUNNING" if devassist.get("state") == "RUNNING" else "UNAVAILABLE",
            "url": DEVASSIST_STATUS_URL,
        },
        "devassist": devassist,
        "external_integrations": external,
    }
