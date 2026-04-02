"""
Quadruple-Ratchet encryption for Sovereignty AI Studio.

Public API
----------
- :class:`QuadRatchetSession` – full four-layer ratchet session
- :class:`MerkleTree`         – append-only Merkle tree with proofs
- :func:`seal` / :func:`unseal` – XChaCha20-Poly1305 AEAD helpers
"""

from sovereignty_ai.ratchet.merkle import MerkleProof, MerkleTree
from sovereignty_ai.ratchet.quad_ratchet import (
    QuadRatchetSession,
    seal,
    unseal,
)

__all__ = [
    "QuadRatchetSession",
    "MerkleTree",
    "MerkleProof",
    "seal",
    "unseal",
]
