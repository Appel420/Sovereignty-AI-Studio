#!/usr/bin/env python3
"""Inventory external integrations without making network calls.

This is deliberately local and read-only. It distinguishes owner-controlled
runtime dependencies from third-party mail transport, which is outside SCAR
scope when the domain is not owned or operated by the device owner.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "node_modules", "external", "__pycache__"}
TEXT_SUFFIXES = {".py", ".js", ".ts", ".html", ".json", ".yaml", ".yml", ".sh", ".md", ".tf"}
URL_RE = re.compile(r"https?://[^\s\"'<>`)]+", re.IGNORECASE)
MAIL_TRANSPORT_TERMS = ("mx", "smtp", "mail exchanger", "mail transport", "spf", "dkim", "dmarc")


def _files() -> list[Path]:
    return [
        path for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts)
        and path.suffix.lower() in TEXT_SUFFIXES
    ]


def _mail_transport_scope(text: str, relative: str) -> str | None:
    lowered = text.lower()
    if any(term in lowered for term in MAIL_TRANSPORT_TERMS):
        return "OUT_OF_SCAR_SCOPE"
    if relative.endswith("SCAR_SCOPE_ADDENDUM_MAIL_TRANSPORT.md"):
        return "DOCUMENTED_SCOPE_BOUNDARY"
    return None


def inventory() -> dict[str, Any]:
    github: list[dict[str, str]] = []
    google: list[dict[str, str]] = []
    terraform: list[str] = []
    oauth: list[dict[str, str]] = []
    workflows: list[dict[str, Any]] = []
    mail_transport: list[dict[str, str]] = []

    for path in _files():
        relative = str(path.relative_to(ROOT))
        if path.suffix.lower() == ".tf":
            terraform.append(relative)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        mail_scope = _mail_transport_scope(text, relative)
        if mail_scope:
            mail_transport.append({"file": relative, "classification": mail_scope})

        for url in URL_RE.findall(text):
            clean = url.rstrip(".,;]")
            lower = clean.lower()
            item = {"file": relative, "url": clean}
            if "api.github.com" in lower or "github.com/" in lower:
                github.append(item)
            if "google" in lower or "gcp" in lower or "googleapis.com" in lower:
                google.append(item)

        if "oauth" in text.lower():
            oauth.append({
                "file": relative,
                "local_policy": relative == "config/local-oauth-policy.json",
                "local_generator": relative == "scripts/oauth_local_generator.py",
                "external_endpoint_reference": bool(re.search(r"https?://", text, re.IGNORECASE)),
            })

        if relative.startswith(".github/workflows/"):
            workflows.append({
                "file": relative,
                "automatic_trigger": bool(re.search(r"^\s*(push|pull_request|schedule|workflow_run)\s*:", text, re.MULTILINE)),
                "hosted_runner": bool(re.search(r"ubuntu|macos|windows", text, re.IGNORECASE)),
            })

    return {
        "mode": "offline",
        "network_access": False,
        "external_calls_made": False,
        "scar_scope_addendum": "docs/compliance/SCAR_SCOPE_ADDENDUM_MAIL_TRANSPORT.md",
        "mail_transport": {
            "references": mail_transport,
            "classification": "OUT_OF_SCAR_SCOPE",
            "owner_control_required": False,
        },
        "local_oauth": {
            "policy": "config/local-oauth-policy.json",
            "generator": "scripts/oauth_local_generator.py",
            "issuer": "local",
            "external_oauth": "disabled",
            "visible": True,
        },
        "github": {
            "api_references": github,
            "runtime_access": bool(github),
            "owner_action_required": True,
        },
        "google_gcp": {
            "references": google,
            "runtime_access": bool(google),
            "owner_action_required": True,
        },
        "terraform": {
            "files": sorted(terraform),
            "present": bool(terraform),
            "runtime_enabled": False,
        },
        "oauth_references": oauth,
        "workflows": workflows,
        "source": "local-read-only-inventory",
    }


def main() -> int:
    print(json.dumps(inventory(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
