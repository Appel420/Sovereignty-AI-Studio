"""TPM attestation compatibility helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AttestationResult:
    provider: str
    verified: bool
    details: dict[str, Any]


class TPMAttester:
    def attest(self) -> AttestationResult:
        return AttestationResult(
            provider="tpm",
            verified=False,
            details={"status": "not_implemented"},
        )

    def status(self) -> dict[str, Any]:
        return {"provider": "tpm", "status": "available"}