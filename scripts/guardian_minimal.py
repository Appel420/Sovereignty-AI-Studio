#!/usr/bin/env python3
"""Genesis 0-1 Minimal Guardian.

Phase A objective:
- Keep the Guardian as one script while it is being exercised.
- Load platform policy from PLATFORM.json.
- Keep checks isolated enough to migrate later into guardian/checks/*.py.
- Produce reports only. Do not delete, rewrite, push, or call external services.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_PATH = ROOT / "PLATFORM.json"

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
    "guardian": {"mode": "report-only", "reports": "automation/reports", "fail_on": ["critical"]},
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

CHECK_CATALOG: Dict[str, Dict[str, str]] = {
    "platform-entrypoint": {
        "title": "Canonical entrypoint",
        "policy": "PLATFORM.entrypoint",
        "recommendation": "Restore the configured SGHV119 entrypoint or update PLATFORM.json intentionally.",
    },
    "command-bus-present": {
        "title": "Command bus present",
        "policy": "PLATFORM.command_bus",
        "recommendation": "Create the configured command bus helper or update PLATFORM.json intentionally.",
    },
    "active-runtime-react": {
        "title": "No React in active runtime",
        "policy": "PLATFORM.runtime.react_active=false",
        "recommendation": "Move legacy React code to archive scope or remove it from the active runtime.",
    },
    "active-runtime-websocket": {
        "title": "No insecure browser WebSocket in active runtime",
        "policy": "PLATFORM.runtime.browser_ws_allowed=false",
        "recommendation": "Use HTTPS request/response by default; use WSS only with TLS, authentication, and explicit streaming need.",
    },
    "active-runtime-provider-api": {
        "title": "No direct UI/provider API calls",
        "policy": "PLATFORM.runtime.external_provider_calls_from_ui_allowed=false",
        "recommendation": "Route provider interoperability through the bridge and policy layer, not directly from UI/runtime modules.",
    },
    "active-runtime-google-meta": {
        "title": "No Google/Meta runtime integration",
        "policy": "PLATFORM.runtime.third_party_runtime_integrations_allowed=false",
        "recommendation": "Remove telemetry/vendor runtime integration or isolate it outside the active runtime.",
    },
    "browser-pqc-claim": {
        "title": "No browser-native PQC key generation claim",
        "policy": "PLATFORM.security.browser_pqc_keygen_allowed=false",
        "recommendation": "Use native/server PQC provider boundaries; do not claim browser-native ML-KEM/ML-DSA key generation.",
    },
    "provider-key-reference": {
        "title": "Provider key reference review",
        "policy": "PLATFORM.mode=local-first and local OAuth/token generation",
        "recommendation": "Verify this is configuration-only and not a committed secret. Keep token generation local.",
    },
}


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
    return (ROOT / policy.get("guardian", {}).get("reports", "automation/reports")).resolve()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def should_skip(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def list_files() -> List[Path]:
    return sorted([p for p in ROOT.rglob("*") if p.is_file() and not should_skip(p)], key=lambda p: rel(p))


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
    if starts_with_any(r, policy.get("archive_candidate_roots", [])):
        return "archive-candidate"
    if starts_with_any(r, policy.get("allowed_active_roots", [])):
        return "active-or-support"
    return "review"


def literal_pattern_to_regex(pattern: str) -> str:
    if pattern.startswith("."):
        return re.escape(pattern) + r"$"
    return re.escape(pattern)


def match_policy_patterns(path: Path, policy: Dict[str, Any]) -> List[Dict[str, str]]:
    r = rel(path)
    haystack = read_text(path) + "\n" + r
    out: List[Dict[str, str]] = []

    for family, patterns in policy.get("forbidden_active_patterns", {}).items():
        for pattern in patterns:
            if re.search(literal_pattern_to_regex(str(pattern)), haystack, re.IGNORECASE):
                out.append({"family": family, "pattern": str(pattern), "source": "PLATFORM.forbidden_active_patterns"})
                break

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
                out.append({"family": family, "pattern": regex, "source": "Guardian.semantic_patterns"})
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


def finding(rule: str, severity: str, path: str, message: str, policy: Dict[str, Any], evidence: Dict[str, Any] | None = None) -> Dict[str, Any]:
    catalog = CHECK_CATALOG.get(rule, {})
    return {
        "rule": rule,
        "title": catalog.get("title", rule),
        "severity": severity,
        "path": path,
        "message": message,
        "policy": catalog.get("policy", "PLATFORM.json"),
        "recommendation": catalog.get("recommendation", "Review PLATFORM.json and update the runtime or policy intentionally."),
        "platform": policy.get("platform", "SGHV119"),
        "platform_version": policy.get("version", "unknown"),
        "evidence": evidence or {},
    }


def check_entrypoint(inv: List[Dict[str, Any]], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    entrypoint = policy.get("entrypoint", "SGHV119.html")
    by_path = {item["path"] for item in inv}
    if entrypoint not in by_path:
        return [finding("platform-entrypoint", "critical", entrypoint, "Canonical UI entrypoint is missing.", policy)]
    return []


def check_command_bus(inv: List[Dict[str, Any]], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    command_bus = policy.get("command_bus", "helpers/command_bus.js")
    by_path = {item["path"] for item in inv}
    if command_bus and command_bus not in by_path:
        return [finding("command-bus-present", "high", command_bus, "Configured command bus is missing.", policy)]
    return []


def check_runtime_patterns(inv: List[Dict[str, Any]], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    runtime = policy.get("runtime", {})
    security = policy.get("security", {})
    entrypoint = policy.get("entrypoint", "SGHV119.html")
    findings: List[Dict[str, Any]] = []

    for item in inv:
        path = item["path"]
        active = item["classification"] != "archive-candidate"
        families = {p["family"] for p in item["patterns"]}
        evidence = {"patterns": item["patterns"], "classification": item["classification"]}

        if active and runtime.get("react_active") is False and "react" in families:
            findings.append(finding("active-runtime-react", "high", path, "React reference exists outside archive-candidate scope.", policy, evidence))

        if active and runtime.get("browser_ws_allowed") is False and "insecure_websocket" in families:
            severity = "high" if path == entrypoint or path.startswith("helpers/") else "medium"
            findings.append(finding("active-runtime-websocket", severity, path, "Insecure browser WebSocket pattern detected in active scope.", policy, evidence))

        if active and runtime.get("external_provider_calls_from_ui_allowed") is False and "external_provider_api" in families:
            severity = "critical" if path == entrypoint or path.startswith("helpers/") else "medium"
            findings.append(finding("active-runtime-provider-api", severity, path, "External AI provider endpoint detected in active scope.", policy, evidence))

        if active and runtime.get("third_party_runtime_integrations_allowed") is False and "google_meta" in families:
            findings.append(finding("active-runtime-google-meta", "high", path, "Google/Meta runtime integration pattern detected in active scope.", policy, evidence))

        if active and security.get("browser_pqc_keygen_allowed") is False and "browser_pqc_claim" in families:
            findings.append(finding("browser-pqc-claim", "critical", path, "Browser-native PQC claim detected.", policy, evidence))

        if "provider_key_reference" in families and not path.endswith(".example"):
            findings.append(finding("provider-key-reference", "medium", path, "Provider key reference detected.", policy, evidence))

    return findings


def run_checks(inv: List[Dict[str, Any]], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]] = [
        check_entrypoint,
        check_command_bus,
        check_runtime_patterns,
    ]
    findings: List[Dict[str, Any]] = []
    for check in checks:
        findings.extend(check(inv, policy))
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


def exit_code(findings: List[Dict[str, Any]], policy: Dict[str, Any]) -> int:
    fail_on = set(policy.get("guardian", {}).get("fail_on", ["critical"]))
    return 1 if any(f.get("severity") in fail_on for f in findings) else 0


def main() -> int:
    policy = load_policy()
    out_dir = report_dir(policy)
    all_files = list_files()
    inv = inventory(all_files, policy)
    dupes = duplicates(all_files)
    findings = run_checks(inv, policy)
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
    return exit_code(findings, policy)


if __name__ == "__main__":
    raise SystemExit(main())
