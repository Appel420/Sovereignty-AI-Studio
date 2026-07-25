"""
sovereignty_ai/ratchet/merkle.py
Binary Merkle tree with BLAKE3 (SHA-256 fallback)
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import List, Tuple

try:
    import blake3 as _blake3
    def _H(data: bytes) -> bytes:
        return _blake3.blake3(data).digest()
except ImportError:
    def _H(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

_DIGEST_LEN = 32
_LEAF_PREFIX = b"\x00"
_INNER_PREFIX = b"\x01"

def _leaf_hash(data: bytes) -> bytes:
    return _H(_LEAF_PREFIX + data)

def _inner_hash(left: bytes, right: bytes) -> bytes:
    return _H(_INNER_PREFIX + left + right)

@dataclass
class MerkleProof:
    leaf_hash: bytes
    leaf_index: int
    path: List[Tuple[bytes, bool]]

class MerkleTree:
    def __init__(self):
        self._leaves: List[bytes] = []
        self._root: bytes = b"\x00" * 32

    @property
    def root(self) -> bytes:
        return self._root

    def append(self, data: bytes) -> int:
        idx = len(self._leaves)
        self._leaves.append(_leaf_hash(data))
        self._recompute_root()
        return idx

    def _recompute_root(self):
        if not self._leaves:
            self._root = b"\x00" * 32
            return
        layer = self._leaves[:]
        while len(layer) > 1:
            next_layer = []
            for i in range(0, len(layer), 2):
                if i + 1 < len(layer):
                    next_layer.append(_inner_hash(layer[i], layer[i+1]))
                else:
                    next_layer.append(layer[i])
            layer = next_layer
        self._root = layer[0]

    def get_proof(self, index: int) -> MerkleProof:
        if index < 0 or index >= len(self._leaves):
            raise IndexError
        path = []
        layer = self._leaves[:]
        idx = index
        while len(layer) > 1:
            next_layer = []
            for i in range(0, len(layer), 2):
                if i + 1 < len(layer):
                    left, right = layer[i], layer[i+1]
                    if i == idx:
                        path.append((right, True))
                        idx = len(next_layer)
                    elif i + 1 == idx:
                        path.append((left, False))
                        idx = len(next_layer)
                    next_layer.append(_inner_hash(left, right))
                else:
                    next_layer.append(layer[i])
                    if i == idx:
                        idx = len(next_layer) - 1
            layer = next_layer
        return MerkleProof(self._leaves[index], index, path)

    @staticmethod
    def verify_proof(root: bytes, leaf_hash: bytes, proof: MerkleProof) -> bool:
        current = leaf_hash
        for sibling, go_right in proof.path:
            if go_right:
                current = _inner_hash(current, sibling)
            else:
                current = _inner_hash(sibling, current)
        return current == root