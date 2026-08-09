from __future__ import annotations

import sys
from pathlib import Path

import pytest
from nacl.signing import SigningKey

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from merkle import (  # noqa: E402
    CheckpointError,
    MerkleTree,
    RollbackDetected,
    RollbackProtectedMerkleTree,
)


def test_inclusion_proofs_verify_for_odd_tree() -> None:
    tree = MerkleTree()
    for index in range(5):
        tree.append(f"leaf-{index}".encode())

    for index in range(5):
        proof = tree.get_proof(index)
        assert proof.verify(tree.root)


def test_inclusion_proof_rejects_wrong_root_and_sibling() -> None:
    tree = MerkleTree()
    tree.append(b"a")
    tree.append(b"b")
    proof = tree.get_proof(0)

    assert not proof.verify(b"x" * len(tree.root))
    proof.path[0] = (b"x" * len(tree.root), True)
    assert not proof.verify(tree.root)


def test_rollback_protection_links_leaves_and_signs_checkpoints() -> None:
    signer = SigningKey.generate()
    tree = RollbackProtectedMerkleTree(signer, signer_key_id="owner-key-v1")

    first, first_checkpoint = tree.append(b"first")
    second, second_checkpoint = tree.append(b"second")

    assert first.previous_leaf_digest is None
    assert second.previous_leaf_digest == first.digest
    assert second.sequence == 2
    assert second.generation == 2
    assert first_checkpoint.verify(signer.verify_key)
    assert second_checkpoint.previous_checkpoint == first_checkpoint.digest()
    assert tree.verify_chain()


def test_state_round_trip_and_trusted_checkpoint() -> None:
    signer = SigningKey.generate()
    source = RollbackProtectedMerkleTree(signer)
    source.append(b"one")
    _, trusted = source.append(b"two")

    restored = RollbackProtectedMerkleTree(signer, trusted_checkpoint=trusted)
    restored.load_state(source.export_state())

    assert restored.root == source.root
    assert restored.sequence == 2
    assert restored.verify_chain()


def test_older_state_is_rejected_as_rollback() -> None:
    signer = SigningKey.generate()
    source = RollbackProtectedMerkleTree(signer)
    source.append(b"one")
    older_state = source.export_state()
    _, trusted = source.append(b"two")

    restored = RollbackProtectedMerkleTree(signer, trusted_checkpoint=trusted)
    with pytest.raises(RollbackDetected):
        restored.load_state(older_state)


def test_modified_previous_leaf_digest_is_rejected() -> None:
    signer = SigningKey.generate()
    source = RollbackProtectedMerkleTree(signer)
    source.append(b"one")
    source.append(b"two")
    state = source.export_state()
    state["leaves"][1]["previous_leaf_digest"] = "f" * 64

    restored = RollbackProtectedMerkleTree(signer)
    with pytest.raises(CheckpointError):
        restored.load_state(state)


def test_modified_checkpoint_signature_is_rejected() -> None:
    signer = SigningKey.generate()
    source = RollbackProtectedMerkleTree(signer)
    source.append(b"one")
    state = source.export_state()
    state["checkpoints"][0]["signature"] = "00" * 64

    restored = RollbackProtectedMerkleTree(signer)
    with pytest.raises(CheckpointError):
        restored.load_state(state)


def test_generation_rollback_is_rejected_even_when_state_is_signed() -> None:
    signer = SigningKey.generate()
    source = RollbackProtectedMerkleTree(signer)
    source.append(b"one")
    _, trusted = source.append(b"two")
    state = source.export_state()
    state["generation"] = 1

    restored = RollbackProtectedMerkleTree(signer, trusted_checkpoint=trusted)
    with pytest.raises(CheckpointError):
        restored.load_state(state)
