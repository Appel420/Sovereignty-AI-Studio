#!/usr/bin/env python3
"""Inventory external integrations without making network calls.

This is deliberately local and read-only. It makes hidden integration paths
visible to the dashboard and CI: GitHub API references, Google/GCP references,
Terraform files, OAuth endpoints, and workflow files.
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


def _files() -> list[Path]:
    return [
        path for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts)
        and path.suffix.lower() in TEXT_SUFFIXES
    ]


def inventory() -> dict[str, Any]:
    github: list[dict[str, str]] = []
    google: list[dict[str, str]] = []
    terraform: list[str] = []
    oauth: list[dict[str, str]] = []
    workflows: list[dict[str, Any]] = []

    for path in _files():
        relative = str(path.relative_to(ROOT))
        if path.suffix.lower() == ".tf":
            terraform.append(relative)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

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
