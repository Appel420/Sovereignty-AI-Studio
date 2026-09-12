from __future__ import annotations

from pathlib import Path

from core.security.tpm_attestation import TPMAttester
from scripts.merkle import MerkleTree, RollbackProtectedMerkleTree
from security.mtls_policy import MTLSConfigurationError, reject_unauthorized, require_client_auth
from nacl.signing import SigningKey


def test_merkle_inclusion_proof_verifies_and_tampering_fails():
    tree = MerkleTree()
    tree.append(b"model-A")
    index = tree.append(b"weights-A")
    tree.append(b"config-A")
    proof = tree.get_proof(index)
    assert proof.verify(tree.root)
    assert not MerkleTree.verify_proof(tree.root, b"\\x00" * 32, proof)


def test_signed_merkle_checkpoint_chain_verifies():
    signer = SigningKey.generate()
    tree = RollbackProtectedMerkleTree(signer, signer_key_id="test")
    tree.append(b"model")
    tree.append(b"weights")
    assert tree.verify_chain()
    state = tree.export_state()
    restored = RollbackProtectedMerkleTree(signer, signer_key_id="test")
    restored.load_state(state)
    assert restored.verify_chain()


def test_tpm_missing_provider_is_deny_not_success():
    result = TPMAttester(checkquote="definitely-not-installed").attest(
        public_key=Path("missing.pub"),
        message=Path("missing.msg"),
        signature=Path("missing.sig"),
        nonce=b"challenge",
        runtime_identity="runtime:test",
        measurement_digest="sha256:test",
    )
    assert result.verified is False
    assert result.details["status"] == "provider_unavailable"


def test_tpm_missing_evidence_is_deny():
    result = TPMAttester(checkquote="definitely-not-installed").attest()
    assert result.verified is False
    assert result.details["status"] == "missing_evidence"


def test_production_mtls_requires_client_ca():
    try:
        require_client_auth(tls_enabled=True, ca_configured=False, production=True)
    except MTLSConfigurationError:
        pass
    else:
        raise AssertionError("production mTLS must fail closed without a client CA")


def test_production_cannot_disable_certificate_verification(monkeypatch):
    monkeypatch.setenv("TLS_REJECT_UNAUTHORIZED", "0")
    assert reject_unauthorized(production=True) is True


def test_development_mtls_can_use_explicit_disable_only_for_nonproduction(monkeypatch):
    monkeypatch.setenv("TLS_REJECT_UNAUTHORIZED", "0")
    assert reject_unauthorized(production=False) is False
