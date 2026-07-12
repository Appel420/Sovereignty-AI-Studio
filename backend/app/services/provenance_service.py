"""Offline Merkle/SHA-256 provenance helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sovereignty_ai.ratchet.merkle import MerkleProof, MerkleTree


class ProvenanceService:
    """Generate and verify Merkle proofs using the existing SHA-256 tree."""

    proof_type = "merkle"
    algorithm = "sha256"

    def generate_proof(self, leaves: list[Any], leaf_index: int) -> dict[str, Any]:
        if not leaves:
            raise ValueError("At least one leaf is required")
        if leaf_index < 0 or leaf_index >= len(leaves):
            raise ValueError("leaf_index out of range")

        normalized_leaves = [self._normalize_leaf(leaf) for leaf in leaves]
        tree = MerkleTree()
        for leaf in normalized_leaves:
            tree.append(leaf)

        proof = tree.proof(leaf_index)
        return self._serialize_proof(proof, len(normalized_leaves), tree.root)

    def verify_proof(self, leaf: Any, proof: dict[str, Any]) -> bool:
        self._validate_proof_type(proof.get("proof_type", self.proof_type))
        self._validate_algorithm(proof.get("algorithm", self.algorithm))

        normalized_leaf = self._normalize_leaf(leaf)
        leaf_hash = self._hash_leaf(normalized_leaf)
        if leaf_hash.hex() != str(proof["leaf_hash"]):
            return False

        merkle_proof = MerkleProof(
            leaf_hash=leaf_hash,
            index=int(proof["leaf_index"]),
            hashes=[bytes.fromhex(hash_value) for hash_value in proof["hashes"]],
            directions=[bool(direction) for direction in proof["directions"]],
        )
        return merkle_proof.verify(bytes.fromhex(str(proof["merkle_root"])))

    @staticmethod
    def _normalize_leaf(leaf: Any) -> bytes:
        if isinstance(leaf, bytes):
            return leaf
        if isinstance(leaf, str):
            return leaf.encode("utf-8")
        return json.dumps(
            leaf,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def _hash_leaf(leaf: bytes) -> bytes:
        return hashlib.sha256(b"\x00" + leaf).digest()

    def _serialize_proof(
        self,
        proof: MerkleProof,
        leaf_count: int,
        merkle_root: bytes,
    ) -> dict[str, Any]:
        return {
            "proof_type": self.proof_type,
            "algorithm": self.algorithm,
            "leaf_index": proof.index,
            "leaf_count": leaf_count,
            "leaf_hash": proof.leaf_hash.hex(),
            "hashes": [hash_value.hex() for hash_value in proof.hashes],
            "directions": proof.directions,
            "merkle_root": merkle_root.hex(),
            "offline": True,
        }

    def _validate_algorithm(self, algorithm: str) -> None:
        if algorithm != self.algorithm:
            raise ValueError("Only Merkle/SHA-256 proofs are supported")

    def _validate_proof_type(self, proof_type: str) -> None:
        if proof_type != self.proof_type:
            raise ValueError("Only Merkle inclusion proofs are supported")


provenance_service = ProvenanceService()
