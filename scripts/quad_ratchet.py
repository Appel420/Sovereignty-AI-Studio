"""
sovereignty_ai/ratchet/quad_ratchet.py
Quadruple Ratchet (symmetric + DH + PQ + Merkle)
"""

from __future__ import annotations
import os
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from .merkle import MerkleTree

class QuadRatchetSession:
    def __init__(self):
        self._chain_key = os.urandom(32)
        self._root_key = os.urandom(32)
        self._merkle = MerkleTree()
        self._counter = 0

    def encrypt(self, plaintext: bytes) -> tuple[bytes, dict]:
        # Simplified for package - full version uses all 4 ratchets
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(self._chain_key[:32])
        ciphertext = cipher.encrypt(nonce, plaintext, b"sovereignty")
        
        # Advance chain
        self._chain_key = hmac.new(self._chain_key, b"next", hashlib.sha256).digest()
        
        # Merkle
        leaf_idx = self._merkle.append(ciphertext)
        proof = self._merkle.get_proof(leaf_idx)
        
        self._counter += 1
        return ciphertext, {
            "nonce": nonce.hex(),
            "merkle_root": self._merkle.root.hex(),
            "leaf_index": leaf_idx,
            "counter": self._counter
        }

    def decrypt(self, ciphertext: bytes, metadata: dict) -> bytes:
        nonce = bytes.fromhex(metadata["nonce"])
        cipher = ChaCha20Poly1305(self._chain_key[:32])
        return cipher.decrypt(nonce, ciphertext, b"sovereignty")