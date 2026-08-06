"""ARM TrustZone compatibility helpers.

No TrustZone provider is active in this repository. Results remain explicitly
unverified until real platform evidence can be independently checked.
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


class ArmTrustZoneAttester:
    def attest(self) -> AttestationResult:
        return AttestationResult(
            provider="arm-trustzone",
            verified=False,
            details={"status": "not_implemented"},
        )

    def status(self) -> dict[str, str]:
        return {"provider": "arm-trustzone", "status": "unavailable"}
