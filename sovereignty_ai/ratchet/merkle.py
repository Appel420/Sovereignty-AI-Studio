"""
Merkle tree implementation for quad-ratchet audit proofs.

Each encrypted blob inserted into a RAG store gets a leaf in the tree.
The root hash changes on every insert so tampering is immediately detectable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import List, Optional


def _hash_leaf(data: bytes) -> bytes:
    """SHA-256 hash of a single leaf (prefixed with 0x00)."""
    return hashlib.sha256(b"\x00" + data).digest()


def _hash_node(left: bytes, right: bytes) -> bytes:
    """SHA-256 hash of an interior node (prefixed with 0x01)."""
    return hashlib.sha256(b"\x01" + left + right).digest()


@dataclass
class MerkleProof:
    """Inclusion proof for a single leaf."""

    leaf_hash: bytes
    index: int
    hashes: List[bytes]  # sibling hashes bottom-up
    directions: List[bool]  # True = sibling is on the right

    def verify(self, root: bytes) -> bool:
        """Recompute root from proof and compare."""
        current = self.leaf_hash
        for sibling, is_right in zip(self.hashes, self.directions):
            if is_right:
                current = _hash_node(current, sibling)
            else:
                current = _hash_node(sibling, current)
        return current == root


@dataclass
class MerkleTree:
    """Append-only Merkle tree."""

    leaves: List[bytes] = field(default_factory=list)

    # -- public API ----------------------------------------------------------

    def append(self, data: bytes) -> int:
        """Add a leaf and return its index."""
        self.leaves.append(_hash_leaf(data))
        return len(self.leaves) - 1

    @property
    def root(self) -> bytes:
        """Compute the current root hash."""
        if not self.leaves:
            return b"\x00" * 32
        return self._build(self.leaves)

    def proof(self, index: int) -> MerkleProof:
        """Generate an inclusion proof for *index*."""
        if index < 0 or index >= len(self.leaves):
            raise IndexError(f"leaf index {index} out of range")
        hashes: List[bytes] = []
        directions: List[bool] = []
        self._collect_proof(self.leaves, index, hashes, directions)
        return MerkleProof(
            leaf_hash=self.leaves[index],
            index=index,
            hashes=hashes,
            directions=directions,
        )

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _build(nodes: List[bytes]) -> bytes:
        layer = list(nodes)
        while len(layer) > 1:
            next_layer: List[bytes] = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else left
                next_layer.append(_hash_node(left, right))
            layer = next_layer
        return layer[0]

    @staticmethod
    def _collect_proof(
        nodes: List[bytes],
        idx: int,
        hashes: List[bytes],
        directions: List[bool],
    ) -> None:
        layer = list(nodes)
        pos = idx
        while len(layer) > 1:
            if pos % 2 == 0:
                sibling_idx = pos + 1 if pos + 1 < len(layer) else pos
                directions.append(True)  # sibling is right
            else:
                sibling_idx = pos - 1
                directions.append(False)  # sibling is left
            hashes.append(layer[sibling_idx])
            next_layer: List[bytes] = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else left
                next_layer.append(_hash_node(left, right))
            layer = next_layer
            pos //= 2
