#!/usr/bin/env python3
"""SGHV119 sanitize/audit automation.

This script is intentionally conservative. It does not delete files.
It generates machine-readable reports that let the repository converge toward
SGHV119 v1.0 without hiding risks or making fake security claims.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Dict, List

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

ACTIVE_ROOTS = {
    "SGHV119.html",
    "agent-workspaces.json",
    "helpers",
    "crypto",
    "node-bridge",
    "bridge.py",
    "backend",
    "agents",
    "ai_core",
    "docs",
    "scripts",
    "rust/pqcrypto-ffi",
}

DIRTY_PATTERNS = {
    "react-runtime": [r"\breact\b", r"react-dom", r"react-scripts", r"\.tsx$", r"\.jsx$"],
    "insecure-websocket": [r"ws://", r"new WebSocket\("],
    "external-ai-provider": [r"api\.openai\.com", r"api\.anthropic\.com", r"api\.x\.ai"],
    "google-meta": [r"googleapis", r"googletagmanager", r"doubleclick", r"facebook", r"meta\.com"],
    "secret-risk": [r"OPENAI_API_KEY\s*=", r"ANTHROPIC_API_KEY\s*=", r"XAI_API_KEY\s*=", r"GH_CLIENT_SECRET\s*="],
    "fake-pqc-claim": [r"browser.*PQC", r"WebCrypto.*ML-KEM", r"WebCrypto.*ML-DSA", r"dirty API"],
}

OWNER_RULES = [
    (re.compile(r"^SGHV119\.html$"), "runtime-ui"),
    (re.compile(r"^helpers/"), "command-bus-and-helpers"),
    (re.compile(r"^crypto/"), "crypto-envelope"),
    (re.compile(r"^rust/pqcrypto-ffi/"), "native-pqc"),
    (re.compile(r"^node-bridge/"), "bridge"),
    (re.compile(r"^backend/"), "backend"),
    (re.compile(r"^agents/"), "agents"),
    (re.compile(r"^ai_core/"), "ai-core"),
    (re.compile(r"^docs/"), "docs"),
    (re.compile(r"^scripts/"), "automation"),
    (re.compile(r"^frontend/"), "legacy-frontend"),
    (re.compile(r"^apps/dashboards/"), "legacy-dashboard"),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def should_skip(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def list_files() -> List[Path]:
    files: List[Path] = []
    for path in ROOT.rglob("*"):
      if should_skip(path):
          continue
      if path.is_file():
          files.append(path)
    return sorted(files, key=lambda p: rel(p))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def category(path: Path) -> str:
    r = rel(path)
    if r in ACTIVE_ROOTS:
        return "active"
    if any(r == root or r.startswith(root + "/") for root in ACTIVE_ROOTS):
        return "active"
    if r.startswith("frontend/") or r.startswith("apps/dashboards/") or r.startswith("external/"):
        return "archive-candidate"
    return "review"


def owner(path: Path) -> str:
    r = rel(path)
    for pattern, name in OWNER_RULES:
        if pattern.search(r):
            return name
    return "unowned"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def scan_findings(path: Path) -> List[Dict[str, str]]:
    r = rel(path)
    text = read_text(path)
    haystack = text + "\n" + r
    findings: List[Dict[str, str]] = []
    for kind, patterns in DIRTY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, haystack, re.IGNORECASE):
                findings.append({"kind": kind, "pattern": pattern})
                break
    return findings


def duplicate_report(files: List[Path]) -> Dict[str, List[str]]:
    buckets: Dict[str, List[str]] = {}
    for path in files:
        digest = sha256(path)
        buckets.setdefault(digest, []).append(rel(path))
    return {digest: paths for digest, paths in buckets.items() if len(paths) > 1}


def dependency_edges(files: List[Path]) -> List[Dict[str, str]]:
    edges: List[Dict[str, str]] = []
    import_re = re.compile(r"(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+)|require\(['\"]([^'\"]+)['\"]\)|<script\s+[^>]*src=['\"]([^'\"]+)['\"])")
    for path in files:
        text = read_text(path)
        if not text:
            continue
        for match in import_re.finditer(text):
            target = next((g for g in match.groups() if g), None)
            if target:
                edges.append({"from": rel(path), "to": target})
    return edges


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    files = list_files()

    inventory = []
    findings = []
    ownership = {}

    for path in files:
        item = {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "category": category(path),
            "owner": owner(path),
        }
        inventory.append(item)
        ownership[item["path"]] = item["owner"]
        for finding in scan_findings(path):
            findings.append({"path": item["path"], **finding})

    duplicates = duplicate_report(files)
    deps = dependency_edges(files)

    migration_plan = {
        "objective": "Converge repository toward SGHV119 v1.0: one UI, one command bus, one bridge, one crypto authority.",
        "active_runtime": [item for item in inventory if item["category"] == "active"],
        "archive_candidates": [item for item in inventory if item["category"] == "archive-candidate"],
        "review_required": [item for item in inventory if item["category"] == "review" or item["owner"] == "unowned"],
        "blocking_findings": findings,
        "next_actions": [
            "Remove React from active runtime path.",
            "Wire SGHV119 helpers through helpers/command_bus.js.",
            "Use native/server PQC provider for real PQC keys; browser must not claim PQC key generation.",
            "Keep HTTPS request/response as default; allow WSS only with TLS, auth, and explicit streaming need.",
            "Archive duplicate dashboards after SGHV119 parity is verified.",
        ],
    }

    outputs = {
        "inventory.json": inventory,
        "ownership.json": ownership,
        "duplicates.json": duplicates,
        "dependency_graph.json": {"edges": deps},
        "sanitization_findings.json": findings,
        "migration_plan.json": migration_plan,
    }

    for name, data in outputs.items():
        (REPORT_DIR / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "files_scanned": len(files),
        "findings": len(findings),
        "duplicates": len(duplicates),
        "archive_candidates": len(migration_plan["archive_candidates"]),
        "review_required": len(migration_plan["review_required"]),
    }
    (REPORT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
