"""SGX DCAP compatibility helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AttestationResult:
    provider: str
    verified: bool
    details: dict[str, Any]


class SGXDCAPAttester:
    def attest(self) -> AttestationResult:
        return AttestationResult(
            provider="sgx-dcap",
            verified=False,
            details={"status": "not_implemented"},
        )

    def status(self) -> dict[str, Any]:
        return {"provider": "sgx-dcap", "status": "available"}