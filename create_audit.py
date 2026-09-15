#!/usr/bin/env python3
"""create_audit.py — restored during live cleanup.
Generates sovereign path audit entries for Sovereignty-AI-Studio.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

AUDIT_LOG = os.path.join(os.getcwd(), "sovereign_audit.jsonl")

def hash_path(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def audit_entry(event: str, detail: str = "") -> dict:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "detail": detail,
        "path_hash": hash_path(detail),
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

if __name__ == "__main__":
    audit_entry("AUDIT_INIT", "sovereign_path_audit restored")
    print("Audit initialized.")
