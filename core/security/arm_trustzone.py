"""ARM TrustZone compatibility helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AttestationResult:
    provider: str
    verified: bool
    details: dict[str, Any]


class ArmTrustZoneAttester:
    def attest(self) -> AttestationResult:
        return AttestationResult(
            provider="arm-trustzone",
            verified=False,
            details={"status": "not_implemented"},
        )

    def status(self) -> dict[str, Any]:
        return {"provider": "arm-trustzone", "status": "available"}