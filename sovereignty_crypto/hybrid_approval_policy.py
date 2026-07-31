from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HybridApprovalPolicy:
    """Verification contract for CryptoKit + liboqs owner approvals.

    CryptoKit signs the owner envelope on Apple devices. liboqs verifies the
    post-quantum signature when the configured ML-DSA provider is available.
    This policy module does not import liboqs or make network calls; callers
    inject the local verification result.
    """

    classical_algorithm: str = "P256.Signing"
    post_quantum_algorithm: str = "ML-DSA-87"
    key_establishment_algorithm: str = "ML-KEM-768"
    required_state_location: str = "DEVICE_FIRST"
    external_persistence: bool = False
    owner_authorization_required: bool = True

    def validate_envelope(self, envelope: dict, *, classical_valid: bool, pq_valid: bool) -> tuple[bool, str]:
        if envelope.get("protocolVersion") != "SG-HYBRID-APPROVAL-1":
            return False, "unsupported approval protocol"
        if envelope.get("decision") != "APPROVED":
            return False, "owner approval is not approved"
        if envelope.get("classicalAlgorithm") != self.classical_algorithm:
            return False, "classical signature algorithm mismatch"
        if envelope.get("postQuantumAlgorithm") != self.post_quantum_algorithm:
            return False, "post-quantum signature algorithm mismatch"
        if not classical_valid:
            return False, "CryptoKit signature verification failed"
        if not pq_valid:
            return False, "liboqs signature verification failed"
        if envelope.get("stateLocation") not in (None, self.required_state_location):
            return False, "state is not device-first"
        if envelope.get("externalPersistence", self.external_persistence):
            return False, "external persistence is not authorized by default"
        return True, "hybrid owner approval verified"
