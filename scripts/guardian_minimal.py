#!/usr/bin/env python3
"""Genesis 0-1 Minimal Guardian.

Purpose:
- Establish SGHV119 freeze/inventory discipline.
- Produce data, not changes.
- Detect obvious architectural drift.
- Never delete, rewrite, push, or call external services.

Policy source:
- PLATFORM.json is authoritative.
- This script should not duplicate platform policy unless a safe default is
  required because PLATFORM.json is missing or invalid.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_PATH = ROOT / "PLATFORM.json"
REPORT_DIR_DEFAULT = ROOT / "automation" / "reports"

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

DEFAULT_POLICY: Dict[str, Any] = {
    "platform": "SGHV119",
    "version": "unknown",
    "entrypoint": "SGHV119.html",
    "command_bus": "helpers/command_bus.js",
    "guardian": {
        "mode": "report-only",
        "reports": "automation/reports",
        "fail_on": ["critical"],
    },
    "runtime": {
        "react_active": False,
        "browser_ws_allowed": False,
        "external_provider_calls_from_ui_allowed": False,
        "third_party_runtime_integrations_allowed": False,
    },
    "security": {
        "native_pqc_required": True,
        "browser_pqc_keygen_allowed": False,
        "dirty_api_keygen_allowed": False,
        "fail_closed_when_crypto_provider_missing": True,
    },
    "allowed_active_roots": [
        "SGHV119.html",
        "PLATFORM.json",
        "agent-workspaces.json",
        "helpers/",
        "crypto/",
        "guardian/",
        "node-bridge/",
        "backend/",
        "agents/",
        "ai_core/",
        "rust/pqcrypto-ffi/",
        "scripts/",
        "docs/",
    ],
    "archive_candidate_roots": ["frontend/", "apps/dashboards/", "external/"],
    "forbidden_active_patterns": {
        "react": ["react", "react-dom", "react-scripts", ".tsx", ".jsx"],
        "insecure_websocket": ["ws://", "new WebSocket("],
        "external_provider_api": ["api.openai.com", "api.anthropic.com", "api.x.ai"],
        "google_meta": ["googleapis", "googletagmanager", "doubleclick", "facebook", "meta.com"],
    },
}

SEVERITY_WEIGHTS = {"critical": 30, "high": 15, "medium": 5, "low": 1, "info": 0}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_policy() -> Dict[str, Any]:
    if not PLATFORM_PATH.exists():
        policy = dict(DEFAULT_POLICY)
        policy["_policy_status"] = "default-policy-platform-json-missing"
        return policy
    try:
        loaded = json.loads(PLATFORM_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        policy = dict(DEFAULT_POLICY)
        policy["_policy_status"] = "default-policy-platform-json-invalid"
        policy["_policy_error"] = str(exc)
        return policy

    # Merge shallow top-level defaults so missing keys do not break Guardian.
    merged = dict(DEFAULT_POLICY)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    merged["_policy_status"] = "loaded-platform-json"
    return merged


def report_dir(policy: Dict[str, Any]) -> Path:
    configured = policy.get("guardian", {}).get("reports", "automation/reports")
    return (ROOT / configured).resolve()


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


def starts_with_any(value: str, prefixes: List[str]) -> bool:
    return any(value == prefix.rstrip("/") or value.startswith(prefix) for prefix in prefixes)


def classify(path: Path, policy: Dict[str, Any]) -> str:
    r = rel(path)
    archive_roots = policy.get("archive_candidate_roots", [])
    active_roots = policy.get("allowed_active_roots", [])
    if starts_with_any(r, archive_roots):
        return "archive-candidate"
    if starts_with_any(r, active_roots):
        return "active-or-support"
    return "review"


def literal_pattern_to_regex(pattern: str) -> str:
    # PLATFORM.json intentionally stores human-readable literals. Convert simple
    # extension markers and words into conservative regexes.
    if pattern.startswith("."):
        return re.escape(pattern) + r"$"
    return re.escape(pattern)


def match_policy_patterns(path: Path, policy: Dict[str, Any]) -> List[Dict[str, str]]:
    r = rel(path)
    text = read_text(path)
    haystack = text + "\n" + r
    out: List[Dict[str, str]] = []
    forbidden = policy.get("forbidden_active_patterns", {})
    for family, patterns in forbidden.items():
        for pattern in patterns:
            regex = literal_pattern_to_regex(str(pattern))
            if re.search(regex, haystack, re.IGNORECASE):
                out.append({"family": family, "pattern": str(pattern)})
                break

    # Extra semantic checks not best represented as literal policy patterns.
    semantic_patterns = {
        "provider_key_reference": [r"OPENAI_API_KEY", r"ANTHROPIC_API_KEY", r"XAI_API_KEY", r"GH_CLIENT_SECRET"],
        "browser_pqc_claim": [
            r"browser[^\n]{0,80}PQC",
            r"WebCrypto[^\n]{0,80}(ML-KEM|ML-DSA|Kyber|Dilithium)",
        ],
    }
    for family, patterns in semantic_patterns.items():
        for regex in patterns:
            if re.search(regex, haystack, re.IGNORECASE):
                out.append({"family": family, "pattern": regex})
                break
    return out


def inventory(all_files: List[Path], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "classification": classify(path, policy),
            "patterns": match_policy_patterns(path, policy),
        }
        for path in all_files
    ]


def duplicates(all_files: List[Path]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = defaultdict(list)
    for path in all_files:
        groups[digest(path)].append(rel(path))
    return {k: v for k, v in groups.items() if len(v) > 1}


def finding(rule: str, severity: str, path: str, message: str, recommendation: str = "") -> Dict[str, Any]:
    return {
        "rule": rule,
        "severity": severity,
        "path": path,
        "message": message,
        "recommendation": recommendation,
    }


def architecture_findings(inv: List[Dict[str, Any]], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    by_path = {item["path"]: item for item in inv}
    entrypoint = policy.get("entrypoint", "SGHV119.html")
    command_bus = policy.get("command_bus", "helpers/command_bus.js")
    runtime = policy.get("runtime", {})
    security = policy.get("security", {})

    if entrypoint not in by_path:
        findings.append(finding(
            "one-ui-entrypoint",
            "critical",
            entrypoint,
            "Canonical UI entrypoint is missing.",
            "Restore the configured SGHV119 entrypoint or update PLATFORM.json intentionally.",
        ))

    if command_bus and command_bus not in by_path:
        findings.append(finding(
            "command-bus-missing",
            "high",
            command_bus,
            "Configured command bus is missing.",
            "Create the command bus helper or update PLATFORM.json intentionally.",
        ))

    for item in inv:
        path = item["path"]
        classification = item["classification"]
        active = classification != "archive-candidate"
        families = {p["family"] for p in item["patterns"]}

        if active and runtime.get("react_active") is False and "react" in families:
            findings.append(finding(
                "no-react-active-runtime",
                "high",
                path,
                "React reference exists outside archive-candidate scope.",
                "Move legacy React code to archive scope or remove it from the active runtime.",
            ))

        if active and runtime.get("browser_ws_allowed") is False and "insecure_websocket" in families:
            severity = "high" if path == entrypoint or path.startswith("helpers/") else "medium"
            findings.append(finding(
                "no-insecure-browser-ws",
                severity,
                path,
                "Insecure browser WebSocket pattern detected in active scope.",
                "Use HTTPS request/response by default; use WSS only with TLS, auth, and explicit streaming need.",
            ))

        if active and runtime.get("external_provider_calls_from_ui_allowed") is False and "external_provider_api" in families:
            severity = "critical" if path == entrypoint or path.startswith("helpers/") else "medium"
            findings.append(finding(
                "no-ui-provider-calls",
                severity,
                path,
                "External AI provider endpoint detected in active scope.",
                "Route provider interoperability through the bridge and policy layer, not directly from UI/runtime modules.",
            ))

        if active and runtime.get("third_party_runtime_integrations_allowed") is False and "google_meta" in families:
            findings.append(finding(
                "no-google-meta-runtime",
                "high",
                path,
                "Google/Meta runtime integration pattern detected in active scope.",
                "Remove telemetry/vendor runtime integration or isolate it outside the active runtime.",
            ))

        if active and security.get("browser_pqc_keygen_allowed") is False and "browser_pqc_claim" in families:
            findings.append(finding(
                "no-browser-pqc-claim",
                "critical",
                path,
                "Browser-native PQC claim detected.",
                "Use native/server PQC provider boundaries; do not claim browser-native ML-KEM/ML-DSA key generation.",
            ))

        if "provider_key_reference" in families and not path.endswith(".example"):
            findings.append(finding(
                "provider-key-reference",
                "medium",
                path,
                "Provider key reference detected.",
                "Verify this is configuration-only and not a committed secret. Keep token generation local.",
            ))

    return findings


def score(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    penalty = sum(SEVERITY_WEIGHTS.get(f.get("severity", "low"), 1) for f in findings)
    value = max(0, 100 - penalty)
    return {
        "score": value,
        "status": "green" if value >= 90 else "yellow" if value >= 70 else "red",
        "penalty": penalty,
        "finding_count": len(findings),
        "critical_count": sum(1 for f in findings if f.get("severity") == "critical"),
        "high_count": sum(1 for f in findings if f.get("severity") == "high"),
        "medium_count": sum(1 for f in findings if f.get("severity") == "medium"),
    }


def write_json(report_dir_path: Path, name: str, data: Any) -> None:
    report_dir_path.mkdir(parents=True, exist_ok=True)
    (report_dir_path / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def exit_code(health: Dict[str, Any], findings: List[Dict[str, Any]], policy: Dict[str, Any]) -> int:
    fail_on = set(policy.get("guardian", {}).get("fail_on", ["critical"]))
    return 1 if any(f.get("severity") in fail_on for f in findings) else 0


def main() -> int:
    policy = load_policy()
    out_dir = report_dir(policy)
    all_files = files()
    inv = inventory(all_files, policy)
    dupes = duplicates(all_files)
    findings = architecture_findings(inv, policy)
    health = score(findings)

    guardian = {
        "phase": "Genesis-0-1",
        "mode": policy.get("guardian", {}).get("mode", "report-only"),
        "timestamp": utc_now(),
        "root": str(ROOT),
        "policy_source": "PLATFORM.json",
        "policy_status": policy.get("_policy_status"),
        "platform": policy.get("platform"),
        "platform_version": policy.get("version"),
        "entrypoint": policy.get("entrypoint"),
        "command_bus": policy.get("command_bus"),
        "file_count": len(all_files),
        "health": health,
    }

    summary = {
        "guardian": guardian,
        "archive_candidates": sum(1 for item in inv if item["classification"] == "archive-candidate"),
        "review_required": sum(1 for item in inv if item["classification"] == "review"),
        "duplicate_groups": len(dupes),
        "finding_count": len(findings),
    }

    write_json(out_dir, "guardian-health.json", guardian)
    write_json(out_dir, "guardian-findings.json", findings)
    write_json(out_dir, "guardian-inventory.json", inv)
    write_json(out_dir, "guardian-duplicates.json", dupes)
    write_json(out_dir, "guardian-score.json", health)
    write_json(out_dir, "guardian-summary.json", summary)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return exit_code(health, findings, policy)


if __name__ == "__main__":
    raise SystemExit(main())
