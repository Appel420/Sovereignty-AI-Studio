"""
Binary Merkle tree and rollback-protected signed checkpoints.

The original MerkleTree API is preserved. RollbackProtectedMerkleTree adds:
- versioned leaves with previous_leaf_digest links;
- monotonic sequence and generation counters;
- signed root checkpoints;
- trusted-checkpoint rollback detection when state is loaded.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List, Tuple

try:
    import blake3 as _blake3

    def _H(data: bytes) -> bytes:
        return _blake3.blake3(data).digest()
except ImportError:  # pragma: no cover - compatibility fallback

    def _H(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

_DIGEST_LEN = 32
_LEAF_PREFIX = b"\x00"
_INNER_PREFIX = b"\x01"


def _leaf_hash(data: bytes) -> bytes:
    return _H(_LEAF_PREFIX + data)


def _inner_hash(left: bytes, right: bytes) -> bytes:
    return _H(_INNER_PREFIX + left + right)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class MerkleProof:
    leaf_hash: bytes
    leaf_index: int
    path: List[Tuple[bytes, bool]]

    def verify(self, root: bytes) -> bool:
        current = self.leaf_hash
        for sibling, go_right in self.path:
            current = _inner_hash(current, sibling) if go_right else _inner_hash(sibling, current)
        return current == root


class MerkleTree:
    def __init__(self):
        self._leaves: List[bytes] = []
        self._root: bytes = b"\x00" * _DIGEST_LEN

    @property
    def root(self) -> bytes:
        return self._root

    @property
    def leaves(self) -> tuple[bytes, ...]:
        return tuple(self._leaves)

    def append(self, data: bytes) -> int:
        idx = len(self._leaves)
        self._leaves.append(_leaf_hash(data))
        self._recompute_root()
        return idx

    def _recompute_root(self) -> None:
        if not self._leaves:
            self._root = b"\x00" * _DIGEST_LEN
            return
        layer = self._leaves[:]
        while len(layer) > 1:
            next_layer = []
            for i in range(0, len(layer), 2):
                right = layer[i + 1] if i + 1 < len(layer) else layer[i]
                next_layer.append(_inner_hash(layer[i], right))
            layer = next_layer
        self._root = layer[0]

    def get_proof(self, index: int) -> MerkleProof:
        if index < 0 or index >= len(self._leaves):
            raise IndexError("leaf index out of range")
        path: list[tuple[bytes, bool]] = []
        layer = self._leaves[:]
        idx = index
        while len(layer) > 1:
            next_layer = []
            for i in range(0, len(layer), 2):
                right_index = i + 1
                if right_index < len(layer):
                    left, right = layer[i], layer[right_index]
                    if i == idx:
                        path.append((right, True))
                        idx = len(next_layer)
                    elif right_index == idx:
                        path.append((left, False))
                        idx = len(next_layer)
                    next_layer.append(_inner_hash(left, right))
                else:
                    next_layer.append(layer[i])
                    if i == idx:
                        idx = len(next_layer) - 1
            layer = next_layer
        return MerkleProof(self._leaves[index], index, path)

    proof = get_proof

    @staticmethod
    def verify_proof(root: bytes, leaf_hash: bytes, proof: MerkleProof) -> bool:
        return MerkleProof(leaf_hash, proof.leaf_index, proof.path).verify(root)


class RollbackDetected(RuntimeError):
    """Persisted state is older than a trusted checkpoint or is inconsistent."""


class CheckpointError(ValueError):
    """A signed checkpoint is malformed or has an invalid signature."""


@dataclass(frozen=True)
class VersionedLeaf:
    digest: str
    sequence: int
    generation: int
    previous_leaf_digest: str | None

    def signable(self) -> bytes:
        return _canonical(asdict(self))


@dataclass(frozen=True)
class SignedCheckpoint:
    generation: int
    sequence: int
    root: str
    latest_leaf_digest: str | None
    previous_checkpoint: str | None
    signer_key_id: str
    signature: str

    def signable_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "sequence": self.sequence,
            "root": self.root,
            "latest_leaf_digest": self.latest_leaf_digest,
            "previous_checkpoint": self.previous_checkpoint,
            "signer_key_id": self.signer_key_id,
        }

    def signable(self) -> bytes:
        return _canonical(self.signable_dict())

    def digest(self) -> str:
        return _H(b"checkpoint-v1" + self.signable() + bytes.fromhex(self.signature)).hex()

    def verify(self, verify_key: VerifyKey) -> bool:
        try:
            verify_key.verify(self.signable(), bytes.fromhex(self.signature))
            return True
        except (BadSignatureError, ValueError):
            return False

    def to_dict(self) -> dict[str, Any]:
        return {**self.signable_dict(), "signature": self.signature, "checkpoint_digest": self.digest()}


class RollbackProtectedMerkleTree:
    """Append-only Merkle state with signed, rollback-detecting checkpoints."""

    def __init__(
        self,
        signing_key: SigningKey,
        signer_key_id: str = "local",
        trusted_checkpoint: SignedCheckpoint | None = None,
    ) -> None:
        self.signing_key = signing_key
        self.verify_key = signing_key.verify_key
        self.signer_key_id = signer_key_id
        self.trusted_checkpoint = trusted_checkpoint
        self.leaves: list[VersionedLeaf] = []
        self.checkpoints: list[SignedCheckpoint] = []
        self.sequence = 0
        self.generation = 0
        self.root = b"\x00" * _DIGEST_LEN

    @property
    def latest_leaf_digest(self) -> str | None:
        return self.leaves[-1].digest if self.leaves else None

    def append(self, data: bytes) -> tuple[VersionedLeaf, SignedCheckpoint]:
        self.sequence += 1
        self.generation += 1
        leaf_digest = _leaf_hash(data).hex()
        leaf = VersionedLeaf(
            digest=leaf_digest,
            sequence=self.sequence,
            generation=self.generation,
            previous_leaf_digest=self.latest_leaf_digest,
        )
        self.leaves.append(leaf)
        tree = MerkleTree()
        for item in self.leaves:
            tree._leaves.append(bytes.fromhex(item.digest))
        tree._recompute_root()
        self.root = tree.root

        checkpoint_body = {
            "generation": self.generation,
            "sequence": self.sequence,
            "root": self.root.hex(),
            "latest_leaf_digest": leaf.digest,
            "previous_checkpoint": self.checkpoints[-1].digest() if self.checkpoints else None,
            "signer_key_id": self.signer_key_id,
        }
        signature = self.signing_key.sign(_canonical(checkpoint_body)).signature.hex()
        checkpoint = SignedCheckpoint(signature=signature, **checkpoint_body)
        self.checkpoints.append(checkpoint)
        return leaf, checkpoint

    def verify_chain(self) -> bool:
        previous: str | None = None
        expected_sequence = 0
        expected_generation = 0
        for leaf in self.leaves:
            expected_sequence += 1
            expected_generation += 1
            if leaf.sequence != expected_sequence or leaf.generation != expected_generation:
                return False
            if leaf.previous_leaf_digest != previous:
                return False
            previous = leaf.digest
        if len(self.checkpoints) != len(self.leaves):
            return False
        previous_checkpoint: str | None = None
        for leaf, checkpoint in zip(self.leaves, self.checkpoints):
            if not checkpoint.verify(self.verify_key):
                return False
            if checkpoint.generation != leaf.generation or checkpoint.sequence != leaf.sequence:
                return False
            if checkpoint.latest_leaf_digest != leaf.digest:
                return False
            if checkpoint.previous_checkpoint != previous_checkpoint:
                return False
            previous_checkpoint = checkpoint.digest()
        return True

    def export_state(self) -> dict[str, Any]:
        return {
            "version": 1,
            "sequence": self.sequence,
            "generation": self.generation,
            "root": self.root.hex(),
            "leaves": [asdict(item) for item in self.leaves],
            "checkpoints": [item.to_dict() for item in self.checkpoints],
        }

    def load_state(self, state: dict[str, Any]) -> None:
        leaves = [VersionedLeaf(**item) for item in state.get("leaves", [])]
        raw_checkpoints = state.get("checkpoints", [])
        checkpoints = [
            SignedCheckpoint(
                generation=item["generation"],
                sequence=item["sequence"],
                root=item["root"],
                latest_leaf_digest=item.get("latest_leaf_digest"),
                previous_checkpoint=item.get("previous_checkpoint"),
                signer_key_id=item["signer_key_id"],
                signature=item["signature"],
            )
            for item in raw_checkpoints
        ]
        candidate = RollbackProtectedMerkleTree(
            self.signing_key,
            self.signer_key_id,
            self.trusted_checkpoint,
        )
        candidate.leaves = leaves
        candidate.checkpoints = checkpoints
        candidate.sequence = int(state.get("sequence", 0))
        candidate.generation = int(state.get("generation", 0))
        candidate.root = bytes.fromhex(state.get("root", (b"\x00" * 32).hex()))
        if not candidate.verify_chain():
            raise CheckpointError("state chain or checkpoint signature is invalid")
        if self.trusted_checkpoint:
            trusted = self.trusted_checkpoint
            if candidate.generation < trusted.generation or candidate.sequence < trusted.sequence:
                raise RollbackDetected("state is older than the trusted checkpoint")
            if candidate.generation == trusted.generation and candidate.root != bytes.fromhex(trusted.root):
                raise RollbackDetected("state conflicts with the trusted checkpoint")
        self.leaves = candidate.leaves
        self.checkpoints = candidate.checkpoints
        self.sequence = candidate.sequence
        self.generation = candidate.generation
        self.root = candidate.root
