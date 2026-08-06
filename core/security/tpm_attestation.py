"""TPM attestation compatibility helpers.

No TPM provider is active in this repository. This module returns an explicit
unverified result and must not be used as production hardware evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AttestationResult:
    provider: str
    verified: bool
    details: dict[str, Any]
    evidence_source: str = "UNVERIFIED"


class TPMAttester:
    def attest(self) -> AttestationResult:
        return AttestationResult(
            provider="tpm",
            verified=False,
            details={"status": "not_implemented"},
        )

    def status(self) -> dict[str, str]:
        return {"provider": "tpm", "status": "unavailable"}
