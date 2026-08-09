"""Black Canary: encrypted leaves with signed rollback-protected Merkle state."""

from .crypto import (
    BLACK_CANARY_SUITE,
    argon2id_derive,
    blake3_digest,
    derive_kek,
)
from .proofs import (
    CheckpointError,
    MerkleProof,
    MerkleTree,
    RollbackDetected,
    RollbackProtectedMerkleTree,
    SignedCheckpoint,
    VersionedLeaf,
)
from .registry import KeyRegistry, TrustAnchor
from .store import MerkleCoordinator, RepoMerkleTree, SecureLeaf

__all__ = [
    "BLACK_CANARY_SUITE",
    "CheckpointError",
    "KeyRegistry",
    "MerkleCoordinator",
    "MerkleProof",
    "MerkleTree",
    "RepoMerkleTree",
    "RollbackDetected",
    "RollbackProtectedMerkleTree",
    "SecureLeaf",
    "SignedCheckpoint",
    "TrustAnchor",
    "VersionedLeaf",
    "argon2id_derive",
    "blake3_digest",
    "derive_kek",
]
