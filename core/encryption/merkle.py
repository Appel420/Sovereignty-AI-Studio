"""Merkle tree helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable


def _hash(data: bytes, algorithm: str = "sha256") -> bytes:
    if algorithm == "blake3":
        try:
            from blake3 import blake3

            return blake3(data).digest()
        except Exception:
            algorithm = "sha256"
    return hashlib.new(algorithm, data).digest()


def _leaf_hash(leaf: bytes, algorithm: str) -> bytes:
    return _hash(b"\x00" + leaf, algorithm)


def _node_hash(left: bytes, right: bytes, algorithm: str) -> bytes:
    return _hash(b"\x01" + left + right, algorithm)


@dataclass(frozen=True)
class MerkleProof:
    index: int
    leaf: bytes
    path: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    root: str = ""
    algorithm: str = "sha256"

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "leaf": self.leaf.hex(),
            "path": list(self.path),
            "root": self.root,
            "algorithm": self.algorithm,
        }


class MerkleTree:
    def __init__(self, leaves: Iterable[bytes | str] | None = None, algorithm: str = "sha256") -> None:
        self.algorithm = algorithm
        self._leaves: list[bytes] = []
        for leaf in leaves or []:
            self.add_leaf(leaf)

    def add_leaf(self, leaf: bytes | str) -> None:
        self._leaves.append(leaf.encode() if isinstance(leaf, str) else bytes(leaf))

    def __len__(self) -> int:
        return len(self._leaves)

    @property
    def leaves(self) -> tuple[bytes, ...]:
        return tuple(self._leaves)

    def root(self) -> str:
        return self._root_bytes().hex()

    def _root_bytes(self) -> bytes:
        if not self._leaves:
            return _hash(b"", self.algorithm)
        nodes = [_leaf_hash(leaf, self.algorithm) for leaf in self._leaves]
        while len(nodes) > 1:
            next_nodes: list[bytes] = []
            for index in range(0, len(nodes), 2):
                left = nodes[index]
                right = nodes[index + 1] if index + 1 < len(nodes) else left
                next_nodes.append(_node_hash(left, right, self.algorithm))
            nodes = next_nodes
        return nodes[0]

    def get_proof(self, index: int) -> MerkleProof:
        if index < 0 or index >= len(self._leaves):
            raise IndexError("leaf index out of range")

        level = [_leaf_hash(leaf, self.algorithm) for leaf in self._leaves]
        proof_path: list[tuple[str, str]] = []
        position = index
        while len(level) > 1:
            if position % 2 == 0:
                sibling_index = position + 1 if position + 1 < len(level) else position
                sibling_side = "right"
            else:
                sibling_index = position - 1
                sibling_side = "left"
            proof_path.append((sibling_side, level[sibling_index].hex()))

            next_level: list[bytes] = []
            for current in range(0, len(level), 2):
                left = level[current]
                right = level[current + 1] if current + 1 < len(level) else left
                next_level.append(_node_hash(left, right, self.algorithm))
            level = next_level
            position //= 2

        return MerkleProof(
            index=index,
            leaf=self._leaves[index],
            path=tuple(proof_path),
            root=self.root(),
            algorithm=self.algorithm,
        )

    @staticmethod
    def verify_proof(leaf: bytes | str, proof: MerkleProof) -> bool:
        current = _leaf_hash(leaf.encode() if isinstance(leaf, str) else bytes(leaf), proof.algorithm)
        for side, sibling_hex in proof.path:
            sibling = bytes.fromhex(sibling_hex)
            current = _node_hash(sibling, current, proof.algorithm) if side == "left" else _node_hash(current, sibling, proof.algorithm)
        return current.hex() == proof.root