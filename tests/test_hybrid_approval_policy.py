"""Verification tests for the local Hybrid owner-approval contract."""
from sovereignty_crypto.hybrid_approval_policy import HybridApprovalPolicy


def envelope(**overrides):
    value = {
        "protocolVersion": "SG-HYBRID-APPROVAL-1",
        "decision": "APPROVED",
        "classicalAlgorithm": "P256.Signing",
        "postQuantumAlgorithm": "ML-DSA-87",
        "stateLocation": "DEVICE_FIRST",
        "externalPersistence": False,
    }
    value.update(overrides)
    return value


def test_hybrid_approval_requires_both_signatures():
    policy = HybridApprovalPolicy()
    assert policy.validate_envelope(envelope(), classical_valid=True, pq_valid=True)[0]
    assert not policy.validate_envelope(envelope(), classical_valid=False, pq_valid=True)[0]
    assert not policy.validate_envelope(envelope(), classical_valid=True, pq_valid=False)[0]


def test_hybrid_approval_rejects_denial_and_external_persistence():
    policy = HybridApprovalPolicy()
    assert not policy.validate_envelope(envelope(decision="DENIED"), classical_valid=True, pq_valid=True)[0]
    assert not policy.validate_envelope(envelope(externalPersistence=True), classical_valid=True, pq_valid=True)[0]


def test_hybrid_approval_rejects_algorithm_or_state_drift():
    policy = HybridApprovalPolicy()
    assert not policy.validate_envelope(envelope(postQuantumAlgorithm="ML-KEM-768"), classical_valid=True, pq_valid=True)[0]
    assert not policy.validate_envelope(envelope(stateLocation="EXTERNAL"), classical_valid=True, pq_valid=True)[0]
