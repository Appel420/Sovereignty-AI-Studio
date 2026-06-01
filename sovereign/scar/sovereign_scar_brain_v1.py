"""Minimal, importable SCAR brain v1 stub."""

from __future__ import annotations


class SovereignScarBrainV1:
    """Temporary placeholder implementation."""


class SovereignSCARBrain:
    """Placeholder for the SovereignSCARBrain v1.1 guardian + attestation engine."""

    def __init__(self) -> None:
        self._strategies: list = []

    def register_strategy(self, strategy) -> None:
        self._strategies.append(strategy)

    def attest(self, payload: dict) -> dict:
        """Run all registered attestation strategies against payload."""
        results = []
        for s in self._strategies:
            results.append(s.verify(payload))
        return {"ok": all(r.get("ok") for r in results), "results": results}


class MLDsa65Strategy:
    """Stub: PQC ML-DSA-65 signature verification strategy."""

    def verify(self, payload: dict) -> dict:
        raise NotImplementedError("ML-DSA-65 verification not yet implemented")


class TpmPcrStrategy:
    """Stub: TPM PCR measurement-based attestation strategy."""

    def verify(self, payload: dict) -> dict:
        raise NotImplementedError("TPM PCR strategy not yet implemented")


class MerkleProofStrategy:
    """Stub: Merkle proof verification strategy."""

    def verify(self, payload: dict) -> dict:
        raise NotImplementedError("Merkle proof verification not yet implemented")
