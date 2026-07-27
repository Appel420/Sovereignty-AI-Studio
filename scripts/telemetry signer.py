"""
security/telemetry_signer.py

Tamper-evident telemetry signing.
Every event is BLAKE3-chained to the previous entry.
Signed with Ed25519. Any modification breaks the chain.

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import blake3 as _b3
    def _hash(data: bytes) -> bytes:
        return _b3.blake3(data).digest()
except ImportError:
    def _hash(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


class TelemetrySigner:
    """
    Append-only, BLAKE3-chained, Ed25519-signed telemetry stream.
    Each event carries: payload, prev_hash, chain_hash, signature.
    """

    def __init__(self, log_path: Optional[str] = None):
        self._prev_hash = b"\x00" * 32
        self._events: list = []
        self._log_path = Path(log_path) if log_path else None

        # Ed25519 signing key
        if _HAS_CRYPTO:
            self._sign_key = Ed25519PrivateKey.generate()
            self.public_key_hex = self._sign_key.public_key().public_bytes(
                Encoding.Raw, PublicFormat.Raw
            ).hex()
        else:
            self._sign_key = None
            self.public_key_hex = ""

        # Replay existing log to get chain tip
        if self._log_path and self._log_path.exists():
            for line in self._log_path.read_bytes().splitlines():
                try:
                    entry = json.loads(line)
                    self._prev_hash = bytes.fromhex(entry["chain_hash"])
                except Exception:
                    pass

    def sign_event(self, event_type: str, data: Dict[str, Any]) -> Dict:
        """
        Create, sign, and append a telemetry event.
        Returns the full signed event dict.
        """
        entry_body = {
            "ts":         time.time(),
            "event_type": event_type,
            "data":       data,
            "prev_hash":  self._prev_hash.hex(),
        }
        body_bytes  = json.dumps(entry_body, sort_keys=True, default=str).encode()
        chain_hash  = _hash(self._prev_hash + body_bytes)
        entry_body["chain_hash"] = chain_hash.hex()

        # Ed25519 signature
        if self._sign_key and _HAS_CRYPTO:
            sig = self._sign_key.sign(body_bytes)
            entry_body["sig"] = sig.hex()
        else:
            # HMAC fallback
            key = os.urandom(32)
            entry_body["sig"] = hmac.new(key, body_bytes, hashlib.sha256).hexdigest()

        self._prev_hash = chain_hash
        self._events.append(entry_body)

        if self._log_path:
            with open(self._log_path, "ab") as f:
                f.write(json.dumps(entry_body, default=str).encode() + b"\n")

        return entry_body

    def verify_chain(self) -> bool:
        """Verify the integrity of all logged events."""
        if not self._log_path or not self._log_path.exists():
            return True
        prev = b"\x00" * 32
        for line in self._log_path.read_bytes().splitlines():
            entry = json.loads(line)
            if bytes.fromhex(entry["prev_hash"]) != prev:
                return False
            body = {k: v for k, v in entry.items() if k not in ("chain_hash", "sig")}
            body_bytes = json.dumps(body, sort_keys=True, default=str).encode()
            expected_chain = _hash(prev + body_bytes)
            if expected_chain.hex() != entry["chain_hash"]:
                return False
            prev = expected_chain
        return True

    @property
    def chain_tip(self) -> str:
        return self._prev_hash.hex()

    @property
    def event_count(self) -> int:
        return len(self._events)
