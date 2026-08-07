"""Encrypted Black Canary leaves and repository Merkle coordination."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap, aes_key_wrap
from nacl.signing import SigningKey

from .crypto import BLACK_CANARY_SUITE, blake3_digest, derive_kek
from .proofs import RollbackProtectedMerkleTree, SignedCheckpoint, VersionedLeaf
from .registry import KeyRegistry


@dataclass(frozen=True)
class SecureLeaf:
    """An AES-GCM encrypted payload with an HKDF/AES-KW wrapped data key."""

    suite: str
    key_id: str
    salt: str
    wrapped_key: str
    nonce: str
    ciphertext: str
    aad_digest: str
    version: int = 1

    @classmethod
    def seal(
        cls,
        payload: bytes,
        *,
        master_key: bytes,
        key_id: str,
        aad: bytes = b"",
        salt: bytes | None = None,
        nonce: bytes | None = None,
    ) -> "SecureLeaf":
        if not payload:
            raise ValueError("payload must not be empty")
        salt = salt or os.urandom(16)
        nonce = nonce or os.urandom(12)
        if len(nonce) != 12:
            raise ValueError("AES-GCM nonce must be 12 bytes")
        kek = derive_kek(master_key, salt=salt, context=key_id.encode())
        data_key = os.urandom(32)
        aad_digest = blake3_digest(aad, domain=b"sovereignty-ai/black-canary/aad/v1/")
        cipher = Cipher(algorithms.AES(data_key), modes.GCM(nonce)).encryptor()
        cipher.authenticate_additional_data(aad_digest)
        ciphertext = cipher.update(payload) + cipher.finalize() + cipher.tag
        return cls(
            suite=BLACK_CANARY_SUITE,
            key_id=key_id,
            salt=salt.hex(),
            wrapped_key=aes_key_wrap(kek, data_key).hex(),
            nonce=nonce.hex(),
            ciphertext=ciphertext.hex(),
            aad_digest=aad_digest.hex(),
        )

    def open(self, *, master_key: bytes, aad: bytes = b"") -> bytes:
        if self.suite != BLACK_CANARY_SUITE or self.version != 1:
            raise ValueError("unsupported SecureLeaf suite or version")
        expected_aad = blake3_digest(aad, domain=b"sovereignty-ai/black-canary/aad/v1/").hex()
        if expected_aad != self.aad_digest:
            raise ValueError("associated data digest mismatch")
        kek = derive_kek(master_key, salt=bytes.fromhex(self.salt), context=self.key_id.encode())
        data_key = aes_key_unwrap(kek, bytes.fromhex(self.wrapped_key))
        raw = bytes.fromhex(self.ciphertext)
        if len(raw) <= 16:
            raise ValueError("ciphertext is truncated")
        decryptor = Cipher(
            algorithms.AES(data_key), modes.GCM(bytes.fromhex(self.nonce), raw[-16:])
        ).decryptor()
        decryptor.authenticate_additional_data(bytes.fromhex(self.aad_digest))
        return decryptor.update(raw[:-16]) + decryptor.finalize()

    def digest(self) -> bytes:
        return blake3_digest(self.canonical(), domain=b"sovereignty-ai/black-canary/leaf/v1/")

    def canonical(self) -> bytes:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":")).encode()


class RepoMerkleTree:
    """Repository-scoped append-only store using signed rollback protection."""

    def __init__(
        self,
        signing_key: SigningKey,
        *,
        signer_key_id: str,
        registry: KeyRegistry,
        trusted_checkpoint: SignedCheckpoint | None = None,
    ) -> None:
        registry.verify_key(signer_key_id).encode()  # fail closed before accepting state
        if registry.verify_key(signer_key_id) != signing_key.verify_key:
            raise ValueError("signing key does not match the registered trust anchor")
        self.registry = registry
        self.signer_key_id = signer_key_id
        self._tree = RollbackProtectedMerkleTree(
            signing_key, signer_key_id=signer_key_id, trusted_checkpoint=trusted_checkpoint
        )
        self._records: list[SecureLeaf] = []

    @property
    def root(self) -> bytes:
        return self._tree.root

    @property
    def sequence(self) -> int:
        return self._tree.sequence

    def append(
        self,
        payload: bytes,
        *,
        master_key: bytes,
        key_id: str,
        aad: bytes = b"",
    ) -> tuple[SecureLeaf, VersionedLeaf, SignedCheckpoint]:
        record = SecureLeaf.seal(payload, master_key=master_key, key_id=key_id, aad=aad)
        leaf, checkpoint = self._tree.append(record.digest())
        self._records.append(record)
        return record, leaf, checkpoint

    def open(self, index: int, *, master_key: bytes, aad: bytes = b"") -> bytes:
        return self._records[index].open(master_key=master_key, aad=aad)

    def export_state(self) -> dict[str, Any]:
        state = self._tree.export_state()
        state["secure_leaves"] = [record.__dict__ for record in self._records]
        return state

    def load_state(self, state: dict[str, Any]) -> None:
        records = [SecureLeaf(**item) for item in state.get("secure_leaves", [])]
        if len(records) != len(state.get("leaves", [])):
            raise ValueError("secure leaf count does not match Merkle leaf count")
        for record, leaf in zip(records, state["leaves"]):
            if record.digest().hex() != leaf["digest"]:
                raise ValueError("secure leaf digest does not match Merkle leaf")
        self._tree.load_state(state)
        self._records = records


class MerkleCoordinator:
    """Coordinates independent repository trees without sharing mutable state."""

    def __init__(self, registry: KeyRegistry) -> None:
        self.registry = registry
        self._trees: dict[str, RepoMerkleTree] = {}

    def add_repository(self, name: str, tree: RepoMerkleTree) -> None:
        if not name or name in self._trees:
            raise ValueError("repository name must be unique and non-empty")
        self._trees[name] = tree

    def get(self, name: str) -> RepoMerkleTree:
        return self._trees[name]
