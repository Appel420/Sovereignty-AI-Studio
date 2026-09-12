"""Fail-closed TPM 2.0 quote verification.

No software fallback is reported as hardware evidence. Missing TPM tooling or
evidence returns an explicit negative result.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AttestationResult:
    provider: str
    verified: bool
    details: dict[str, Any] = field(default_factory=dict)
    evidence_source: str = "UNVERIFIED"


class HardwareAttestationError(RuntimeError):
    """Raised for malformed verifier configuration/evidence."""


class TPMAttester:
    """Verify TPM 2.0 quotes without treating software state as hardware proof."""

    def __init__(self, *, checkquote: str = "tpm2_checkquote", timeout: float = 10.0) -> None:
        self.checkquote = checkquote
        self.timeout = timeout

    def status(self) -> dict[str, str]:
        return {"provider": "tpm", "status": "available" if shutil.which(self.checkquote) else "unavailable"}

    def attest(
        self,
        *,
        public_key: Path | str | None = None,
        message: Path | str | None = None,
        signature: Path | str | None = None,
        nonce: bytes | None = None,
        runtime_identity: str | None = None,
        measurement_digest: str | None = None,
    ) -> AttestationResult:
        public_key = public_key or os.getenv("TPM_ATTEST_PUBLIC_KEY")
        message = message or os.getenv("TPM_ATTEST_MESSAGE")
        signature = signature or os.getenv("TPM_ATTEST_SIGNATURE")
        runtime_identity = runtime_identity or os.getenv("TPM_ATTEST_RUNTIME_IDENTITY")
        measurement_digest = measurement_digest or os.getenv("TPM_ATTEST_MEASUREMENT_DIGEST")
        if nonce is None:
            nonce_hex = os.getenv("TPM_ATTEST_NONCE_HEX", "")
            try:
                nonce = bytes.fromhex(nonce_hex) if nonce_hex else b""
            except ValueError:
                return AttestationResult("tpm", False, {"status": "invalid_nonce"})

        missing = [
            name for name, value in {
                "public_key": public_key,
                "message": message,
                "signature": signature,
                "nonce": nonce,
                "runtime_identity": runtime_identity,
                "measurement_digest": measurement_digest,
            }.items() if not value
        ]
        if missing:
            return AttestationResult("tpm", False, {"status": "missing_evidence", "missing": missing})

        if not shutil.which(self.checkquote):
            return AttestationResult("tpm", False, {"status": "provider_unavailable", "command": self.checkquote})

        command = [self.checkquote, "-u", str(public_key), "-m", str(message), "-s", str(signature), "-g", "sha256", "-q", bytes(nonce).hex()]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired:
            return AttestationResult("tpm", False, {"status": "verification_timeout"})
        except OSError as exc:
            return AttestationResult("tpm", False, {"status": "verification_error", "error": str(exc)})

        if completed.returncode != 0:
            return AttestationResult("tpm", False, {"status": "quote_invalid", "exit_code": completed.returncode, "stderr": completed.stderr[-1000:]})

        return AttestationResult(
            "tpm", True,
            {
                "status": "verified",
                "runtime_identity": str(runtime_identity),
                "measurement_digest": str(measurement_digest),
                "nonce_sha256": hashlib.sha256(bytes(nonce)).hexdigest(),
            },
            "TPM2_QUOTE",
        )
