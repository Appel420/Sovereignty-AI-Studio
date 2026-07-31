#!/usr/bin/env python3
"""
compliance_scan.py — Automated Compliance Scanner for Gate.one

Scans for key compliance controls across the Gate One codebase.
Supports JSON output for automation and CI integration.
"""

import argparse
import json
import re
from pathlib import Path
from datetime import datetime

def scan_for_pqc_usage(root: Path) -> dict:
    """Check for ML-DSA-65 / Dilithium usage in code."""
    findings = []
    for py_file in root.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            if "ML-DSA-65" in content or "oqs.Signature" in content:
                findings.append(str(py_file))
        except Exception:
            continue
    return {"pqc_usage_found": len(findings) > 0, "files": findings}


def scan_for_immutable_logging(root: Path) -> dict:
    """Check for immutable / append-only logging patterns."""
    findings = []
    patterns = ["append", "immutable", "jsonl", "audit.log", "write.*log"]
    for py_file in root.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8").lower()
            if any(p in content for p in patterns):
                findings.append(str(py_file))
        except Exception:
            continue
    return {"immutable_logging_found": len(findings) > 0, "files": findings}


def scan_for_blocked_dependencies(root: Path) -> dict:
    """Scan for any references to blocked companies (should return zero)."""
    blocked = ["google", "meta", "vercel", "firebase", "gemini", "ollama"]
    findings = []
    for f in root.rglob("*"):
        if f.is_file():
            try:
                content = f.read_text(encoding="utf-8", errors="ignore").lower()
                for b in blocked:
                    if b in content:
                        findings.append({"file": str(f), "blocked_term": b})
            except Exception:
                continue
    return {"blocked_references_found": len(findings) > 0, "violations": findings}


def scan_for_manifest_signing(root: Path) -> dict:
    """Check if export scripts properly sign manifests."""
    findings = []
    for py_file in root.rglob("export*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            if "sign" in content.lower() and ("manifest" in content.lower() or "MANIFEST" in content):
                findings.append(str(py_file))
        except Exception:
            continue
    return {"manifest_signing_implemented": len(findings) > 0, "files": findings}


def run_compliance_scan(root_path: str = ".") -> dict:
    root = Path(root_path).resolve()

    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "scan_root": str(root),
        "pqc": scan_for_pqc_usage(root),
        "immutable_logging": scan_for_immutable_logging(root),
        "blocked_dependencies": scan_for_blocked_dependencies(root),
        "manifest_signing": scan_for_manifest_signing(root),
    }

    # Overall compliance score (simple heuristic)
    score = 0
    if results["pqc"]["pqc_usage_found"]: score += 30
    if results["immutable_logging"]["immutable_logging_found"]: score += 25
    if not results["blocked_dependencies"]["blocked_references_found"]: score += 25
    if results["manifest_signing"]["manifest_signing_implemented"]: score += 20

    results["compliance_score"] = score
    results["status"] = "PASS" if score >= 70 else "REVIEW_NEEDED"

    return results


def main():
    parser = argparse.ArgumentParser(description="Gate.one Automated Compliance Scanner")
    parser.add_argument("--path", default=".", help="Root path to scan")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    report = run_compliance_scan(args.path)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"\n=== Gate.one Compliance Scan ===")
        print(f"Status: {report['status']} | Score: {report['compliance_score']}/100")
        print(f"PQC Usage: {'✓' if report['pqc']['pqc_usage_found'] else '✗'}")
        print(f"Immutable Logging: {'✓' if report['immutable_logging']['immutable_logging_found'] else '✗'}")
        print(f"Blocked Dependencies: {'✗ Found' if report['blocked_dependencies']['blocked_references_found'] else '✓ Clean'}")
        print(f"Manifest Signing: {'✓' if report['manifest_signing']['manifest_signing_implemented'] else '✗'}")
        print("=================================\n")


if __name__ == "__main__":
    main()