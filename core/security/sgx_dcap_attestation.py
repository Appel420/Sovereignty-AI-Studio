"""SGX DCAP compatibility helpers.

No SGX DCAP provider is active in this repository. Results remain explicitly
unverified until a real provider and independent verifier are integrated.
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


class SGXDCAPAttester:
    def attest(self) -> AttestationResult:
        return AttestationResult(
            provider="sgx-dcap",
            verified=False,
            details={"status": "not_implemented"},
        )

    def status(self) -> dict[str, str]:
        return {"provider": "sgx-dcap", "status": "unavailable"}
