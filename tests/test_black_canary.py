from __future__ import annotations

import os

import pytest
from nacl.signing import SigningKey

from sovereignty_ai.black_canary import KeyRegistry, RepoMerkleTree, SecureLeaf, TrustAnchor


def _registry(signer: SigningKey) -> KeyRegistry:
    registry_signer = SigningKey.generate()
    registry = KeyRegistry(registry_signer.verify_key)
    anchor = TrustAnchor("owner-v1", signer.verify_key.encode().hex())
    payload, signature = registry.signed_anchor(anchor, registry_signer)
    assert payload["key_id"] == "owner-v1"
    registry.register_signed(anchor, signature)
    return registry


def test_secure_leaf_round_trip_and_tamper_rejection() -> None:
    key = os.urandom(32)
    leaf = SecureLeaf.seal(b"secret", master_key=key, key_id="owner-v1", aad=b"repo")
    assert leaf.open(master_key=key, aad=b"repo") == b"secret"
    with pytest.raises(Exception):
        leaf.open(master_key=key, aad=b"wrong")


def test_repo_tree_links_signed_checkpoints_and_restores() -> None:
    signer = SigningKey.generate()
    registry = _registry(signer)
    tree = RepoMerkleTree(signer, signer_key_id="owner-v1", registry=registry)
    key = os.urandom(32)
    first = tree.append(b"one", master_key=key, key_id="data-v1", aad=b"r")
    second = tree.append(b"two", master_key=key, key_id="data-v1", aad=b"r")
    assert second[1].previous_leaf_digest == first[1].digest
    assert second[2].previous_checkpoint == first[2].digest()
    assert tree.open(1, master_key=key, aad=b"r") == b"two"

    restored = RepoMerkleTree(
        signer,
        signer_key_id="owner-v1",
        registry=registry,
        trusted_checkpoint=second[2],
    )
    restored.load_state(tree.export_state())
    assert restored.root == tree.root
