#!/usr/bin/env python3
"""Genesis 0-1 Minimal Guardian.

Purpose:
- Establish SGHV119 freeze/inventory discipline.
- Produce data, not changes.
- Detect obvious architectural drift.
- Never delete, rewrite, push, or call external services.

This is the first Guardian, intentionally small.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "automation" / "reports"

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}

FREEZE_RULES = [
    {
        "id": "one-ui-entrypoint",
        "description": "SGHV119.html is the canonical UI entrypoint.",
        "severity": "high",
    },
    {
        "id": "no-react-active-runtime",
        "description": "React must not be part of the active runtime.",
        "severity": "high",
    },
    {
        "id": "no-insecure-browser-ws",
        "description": "Browser ws:// control channels are not allowed in active runtime.",
        "severity": "high",
    },
    {
        "id": "no-ui-provider-calls",
        "description": "UI must not call external AI provider APIs directly.",
        "severity": "critical",
    },
    {
        "id": "pqc-fail-closed",
        "description": "Browser must not claim native PQC key generation without a local/native provider.",
        "severity": "critical",
    },
]

PATTERNS = {
    "react": [r"\bReact\b", r"react-dom", r"react-scripts", r"\.tsx$", r"\.jsx$"],
    "browser_ws": [r"ws://", r"new\s+WebSocket\s*\("],
    "external_ai_api": [r"api\.openai\.com", r"api\.anthropic\.com", r"api\.x\.ai"],
    "provider_key": [r"OPENAI_API_KEY", r"ANTHROPIC_API_KEY", r"XAI_API_KEY", r"GH_CLIENT_SECRET"],
    "pqc_claim": [r"browser[^\n]{0,80}PQC", r"WebCrypto[^\n]{0,80}(ML-KEM|ML-DSA|Kyber|Dilithium)", r"native PQC"],
}

ACTIVE_ALLOWLIST_PREFIXES = (
    "SGHV119.html",
    "agent-workspaces.json",
    "helpers/",
    "crypto/",
    "node-bridge/",
    "backend/",
    "agents/",
    "ai_core/",
    "rust/pqcrypto-ffi/",
    "scripts/",
    "docs/",
)

LEGACY_PREFIXES = (
    "frontend/",
    "apps/dashboards/",
    "external/",
)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def should_skip(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def files() -> List[Path]:
    return sorted(
        [p for p in ROOT.rglob("*") if p.is_file() and not should_skip(p)],
        key=lambda p: rel(p),
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 128), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(path: Path) -> str:
    r = rel(path)
    if r == "SGHV119.html" or any(r.startswith(prefix) for prefix in ACTIVE_ALLOWLIST_PREFIXES):
        if any(r.startswith(prefix) for prefix in LEGACY_PREFIXES):
            return "archive-candidate"
        return "active-or-support"
    if any(r.startswith(prefix) for prefix in LEGACY_PREFIXES):
        return "archive-candidate"
    return "review"


def match_patterns(path: Path) -> List[Dict[str, str]]:
    r = rel(path)
    text = read_text(path)
    haystack = text + "\n" + r
    out: List[Dict[str, str]] = []
    for family, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, haystack, re.IGNORECASE):
                out.append({"family": family, "pattern": pattern})
                break
    return out


def inventory(all_files: List[Path]) -> List[Dict[str, Any]]:
    return [
        {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "classification": classify(path),
            "patterns": match_patterns(path),
        }
        for path in all_files
    ]


def duplicates(all_files: List[Path]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = defaultdict(list)
    for path in all_files:
        groups[digest(path)].append(rel(path))
    return {k: v for k, v in groups.items() if len(v) > 1}


def architecture_findings(inv: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    by_path = {item["path"]: item for item in inv}

    if "SGHV119.html" not in by_path:
        findings.append({
            "rule": "one-ui-entrypoint",
            "severity": "critical",
            "path": "SGHV119.html",
            "message": "Canonical UI entrypoint is missing.",
        })

    for item in inv:
        path = item["path"]
        classification = item["classification"]
        families = {p["family"] for p in item["patterns"]}

        if "react" in families and classification != "archive-candidate":
            findings.append({
                "rule": "no-react-active-runtime",
                "severity": "high",
                "path": path,
                "message": "React reference exists outside archive-candidate scope.",
            })

        if "browser_ws" in families and path == "SGHV119.html":
            findings.append({
                "rule": "no-insecure-browser-ws",
                "severity": "high",
                "path": path,
                "message": "SGHV119.html contains browser WebSocket control logic.",
            })

        if "external_ai_api" in families and path == "SGHV119.html":
            findings.append({
                "rule": "no-ui-provider-calls",
                "severity": "critical",
                "path": path,
                "message": "UI references external AI provider API directly.",
            })

        if "provider_key" in families and not path.endswith(".example"):
            findings.append({
                "rule": "provider-key-reference",
                "severity": "medium",
                "path": path,
                "message": "Provider key reference detected; verify it is configuration-only and not a committed secret.",
            })

    return findings


def score(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    weights = {"critical": 30, "high": 15, "medium": 5, "low": 1}
    penalty = sum(weights.get(f.get("severity", "low"), 1) for f in findings)
    value = max(0, 100 - penalty)
    return {
        "score": value,
        "status": "green" if value >= 90 else "yellow" if value >= 70 else "red",
        "penalty": penalty,
        "finding_count": len(findings),
    }


def write_json(name: str, data: Any) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    all_files = files()
    inv = inventory(all_files)
    dupes = duplicates(all_files)
    findings = architecture_findings(inv)
    health = score(findings)

    guardian = {
        "phase": "Genesis-0-1",
        "mode": "report-only",
        "root": str(ROOT),
        "rules": FREEZE_RULES,
        "file_count": len(all_files),
        "health": health,
    }

    write_json("guardian-health.json", guardian)
    write_json("guardian-findings.json", findings)
    write_json("guardian-inventory.json", inv)
    write_json("guardian-duplicates.json", dupes)
    write_json("guardian-score.json", health)

    print(json.dumps({"guardian": guardian, "findings": findings[:10]}, indent=2, sort_keys=True))
    return 1 if health["status"] == "red" else 0


if __name__ == "__main__":
    raise SystemExit(main())
