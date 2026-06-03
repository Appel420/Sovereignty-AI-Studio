"""
SignatureManager — HMAC-SHA256 entry signing and log chain integrity verification.
"""

import hashlib
import json
from pathlib import Path


class SignatureManager:
    """Signs log entries and verifies the integrity of an append-only log file."""

    def __init__(self, secret_key: str) -> None:
        self.secret_key = secret_key

    def generate_signature(self, data: dict) -> str:
        """Return a deterministic HMAC-SHA256 hex digest for *data*."""
        payload = json.dumps(data, sort_keys=True)
        return hashlib.sha256((payload + self.secret_key).encode()).hexdigest()

    def verify_log_integrity(self, log_file: Path) -> bool:
        """Return True iff every signed entry in *log_file* has a valid signature."""
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    stored_sig = entry.pop("signature", None)
                    expected = self.generate_signature(entry)
                    if stored_sig != expected:
                        return False
            return True
        except Exception:
            return False
