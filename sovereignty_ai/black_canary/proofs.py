"""Thin, stable access layer over the repository Merkle implementation."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from merkle import (  # noqa: E402
    CheckpointError,
    MerkleProof,
    MerkleTree,
    RollbackDetected,
    RollbackProtectedMerkleTree,
    SignedCheckpoint,
    VersionedLeaf,
)

__all__ = [
    "CheckpointError",
    "MerkleProof",
    "MerkleTree",
    "RollbackDetected",
    "RollbackProtectedMerkleTree",
    "SignedCheckpoint",
    "VersionedLeaf",
]
