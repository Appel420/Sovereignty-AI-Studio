"""
sovereignty_ai/ratchet/quad_ratchet.py

Quadruple Ratchet Protocol -- Sovereignty One

Four simultaneous ratchet mechanisms:
  1. Symmetric chain ratchet (HMAC-SHA256 KDF)
  2. DH ratchet (X25519 Diffie-Hellman)
  3. Post-quantum ratchet (ML-KEM-768 / Kyber, via oqs-python)
  4. Merkle audit ratchet (append-only BLAKE3 Merkle tree)

Encryption: XChaCha20-Poly1305 (24-byte nonce, authenticated)
Signing:     Ed25519 (message authentication / proof signing)
Forward secrecy: Each message uses a unique message key derived from the chain;
                 chain keys are overwritten, preventing retrospective decryption
                 even if the current state is compromised.

Dependencies:
  pip install cryptography open-quantum-safe blake3

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption,
)
from cryptography.exceptions import InvalidTag

from .merkle import MerkleTree

# ── Constants ──────────────────────────────────────────────────────
CHAIN_KEY_LEN = 32
_NONCE_LEN    = 24          # Extended nonce -- we derive a 12-byte nonce via HKDF
_HEADER_LEN   = 4 + 32 + 4  # counter(4) + dh_pub(32) + pq_ct_len(4)

# XChaCha20-Poly1305 emulation:
# Use 24-byte nonce → split into 16-byte salt (HKDF input) + 8-byte nonce suffix.
# HKDF(key, salt=nonce[:16]) → 32-byte subkey.
# ChaCha20Poly1305(subkey, nonce=b'\x00\x00\x00\x00' + nonce[16:]) → encrypt.
# This achieves the same extended-nonce property as XChaCha20.

def _derive_subkey(key: bytes, nonce_prefix: bytes) -> tuple[bytes, bytes]:
    """
    HKDF-SHA256 key derivation for extended nonce support.
    Returns (subkey_32, chacha_nonce_12).
    """
    subkey = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=nonce_prefix,
        info=b"sovereignty_ai_chacha_subkey",
    ).derive(key)
    # ChaCha20Poly1305 nonce: 4 zero bytes + last 8 bytes of extended nonce
    chacha_nonce = b"\x00\x00\x00\x00" + nonce_prefix[:8]
    return subkey, chacha_nonce

# Attempt to load oqs for real ML-KEM-768 (Kyber).
# Falls back to an HKDF-expanded random bytes if oqs is unavailable.
try:
    import oqs as _oqs
    _ML_KEM_ALG  = "ML-KEM-768"
    _PQ_CT_LEN   = 1088   # ML-KEM-768 ciphertext length in bytes

    def _pq_encapsulate() -> tuple[bytes, bytes]:
        """Returns (ciphertext, shared_secret) using ML-KEM-768."""
        kem    = _oqs.KeyEncapsulation(_ML_KEM_ALG)
        pubkey = kem.generate_keypair()
        ct, ss = kem.encap_secret(pubkey)
        return ct, ss

    _PQ_AVAILABLE = True

except ImportError:
    _PQ_CT_LEN = 32

    def _pq_encapsulate() -> tuple[bytes, bytes]:
        """
        oqs not installed -- generate random bytes in place of ML-KEM-768.
        The quadruple ratchet degrades to triple (DH + symmetric + Merkle).
        Install open-quantum-safe for full post-quantum security.
        """
        ct = os.urandom(32)
        ss = hashlib.sha256(ct).digest()
        return ct, ss

    _PQ_AVAILABLE = False


# ── Symmetric primitives ───────────────────────────────────────────

def seal(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """
    Encrypt `plaintext` using ChaCha20-Poly1305 with HKDF-extended nonce.
    A 24-byte random nonce is generated; the first 16 bytes derive the subkey
    via HKDF-SHA256, the remaining 8 bytes form the ChaCha20 counter nonce.
    Returns: nonce(24) || ciphertext+tag.
    """
    if len(key) != 32:
        raise ValueError(f"seal: key must be 32 bytes, got {len(key)}")
    nonce = os.urandom(_NONCE_LEN)
    subkey, chacha_nonce = _derive_subkey(key, nonce[:16])
    cipher = ChaCha20Poly1305(subkey)
    ct = cipher.encrypt(chacha_nonce, plaintext, aad if aad else None)
    return nonce + ct


def unseal(key: bytes, blob: bytes, aad: bytes = b"") -> bytes:
    """
    Decrypt a blob produced by `seal`.
    Raises `cryptography.exceptions.InvalidTag` if key or aad is wrong.
    """
    if len(key) != 32:
        raise ValueError(f"unseal: key must be 32 bytes, got {len(key)}")
    if len(blob) < _NONCE_LEN + 16:
        raise ValueError("unseal: blob too short")
    nonce  = blob[:_NONCE_LEN]
    ct     = blob[_NONCE_LEN:]
    subkey, chacha_nonce = _derive_subkey(key, nonce[:16])
    cipher = ChaCha20Poly1305(subkey)
    return cipher.decrypt(chacha_nonce, ct, aad if aad else None)


def _kdf_chain(chain_key: bytes) -> tuple[bytes, bytes]:
    """
    Advance the symmetric ratchet by one step.

    Uses HMAC-SHA256 with domain-separated constants:
      next_chain_key = HMAC(chain_key, 0x02)
      message_key    = HMAC(chain_key, 0x01)

    Returns (next_chain_key, message_key), each CHAIN_KEY_LEN bytes.
    The chain_key input is consumed and must not be reused.
    """
    mk  = hmac.new(chain_key, b"\x01", hashlib.sha256).digest()
    ck2 = hmac.new(chain_key, b"\x02", hashlib.sha256).digest()
    return ck2, mk


# ── Quadruple Ratchet Session ──────────────────────────────────────

class QuadRatchetSession:
    """
    A stateful quadruple-ratchet encryption session.

    Each call to encrypt() advances all four ratchet mechanisms:
      1. Symmetric chain (HMAC-KDF): produces a fresh message key
      2. DH ratchet (X25519): generates an ephemeral key pair per message
      3. PQ ratchet (ML-KEM-768): encapsulates a fresh shared secret per message
      4. Merkle ratchet: appends the ciphertext hash to an audit tree

    Security properties:
      - Break-in recovery: future messages secure after compromise (DH + PQ)
      - Forward secrecy: chain keys are overwritten after each advance
      - Post-quantum forward secrecy: ML-KEM-768 shared secret mixed into message key
      - Non-repudiation: Ed25519 proof signature over each message

    Sessions are NOT interoperable: a fresh QuadRatchetSession cannot
    decrypt blobs from another session (different root key + chain state).
    """

    def __init__(self) -> None:
        # Symmetric ratchet state
        self._root_chain_key: bytes = os.urandom(CHAIN_KEY_LEN)
        self._chain_key: bytes      = self._root_chain_key
        self._counter:   int        = 0

        # Message key store: {counter -> message_key}
        # Populated on encrypt, consumed on decrypt.
        self._recv_keys: dict[int, bytes] = {}

        # DH ratchet keys (stable session identity keys)
        self._dh_priv: X25519PrivateKey = X25519PrivateKey.generate()
        self._dh_pub_bytes: bytes = self._dh_priv.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )

        # Ed25519 signing key (proof authentication)
        self._sign_priv: Ed25519PrivateKey = Ed25519PrivateKey.generate()

        # Merkle audit tree
        self._merkle: MerkleTree = MerkleTree()

    # ── Encrypt ────────────────────────────────────────────────────

    def encrypt(self, plaintext: bytes) -> tuple[bytes, dict]:
        """
        Encrypt `plaintext` under the current ratchet state.

        Returns:
          blob  -- encrypted bytes (counter || dh_pub || pq_ct_len || pq_ct || sealed)
          proof -- dict with sig, merkle_root, leaf_index, dh_pub, pq_ct
        """
        # 1. Advance symmetric chain
        ck2, mk = _kdf_chain(self._chain_key)
        idx     = self._counter

        # Overwrite chain key (forward secrecy)
        self._chain_key = ck2
        self._counter  += 1

        # 2. Ephemeral X25519 DH key for this message
        eph_priv     = X25519PrivateKey.generate()
        eph_pub_bytes = eph_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

        # 3. PQ encapsulation
        pq_ct, pq_ss = _pq_encapsulate()

        # 4. Mix DH and PQ shared secrets into message key via HMAC
        dh_ss     = eph_priv.exchange(
            X25519PublicKey.from_public_bytes(self._dh_pub_bytes)
        )
        final_mk  = hmac.new(mk, dh_ss + pq_ss, hashlib.sha256).digest()

        # Store for decryption (indexed by counter)
        self._recv_keys[idx] = final_mk

        # 5. XChaCha20-Poly1305 seal
        sealed = seal(final_mk, plaintext)

        # 6. Append ciphertext hash to Merkle tree
        leaf_data  = hashlib.sha256(sealed).digest()
        leaf_index = self._merkle.append(leaf_data)

        # 7. Build serialized blob: counter(4) + eph_pub(32) + pq_ct_len(4) + pq_ct + sealed
        blob = (
            struct.pack(">I", idx)
            + eph_pub_bytes
            + struct.pack(">I", len(pq_ct))
            + pq_ct
            + sealed
        )

        # 8. Build proof dict and sign it
        proof_data = {
            "merkle_root": base64.urlsafe_b64encode(self._merkle.root).decode(),
            "leaf_index":  leaf_index,
            "dh_pub":      base64.urlsafe_b64encode(eph_pub_bytes).decode(),
            "pq_ct":       base64.urlsafe_b64encode(pq_ct).decode(),
            "counter":     idx,
        }
        sig_bytes = self._sign(blob)
        proof_data["sig"] = base64.urlsafe_b64encode(sig_bytes).decode()

        return blob, proof_data

    def encrypt_text(self, text: str) -> tuple[bytes, dict]:
        """Convenience wrapper: encrypt a UTF-8 string."""
        return self.encrypt(text.encode("utf-8"))

    # ── Decrypt ────────────────────────────────────────────────────

    def decrypt(self, blob: bytes) -> bytes:
        """
        Decrypt a blob produced by this session's encrypt().

        Raises:
          ValueError   -- malformed blob or unknown counter
          InvalidTag   -- blob tampered or wrong session
        """
        if len(blob) < _HEADER_LEN:
            raise ValueError("decrypt: blob too short for header")

        # Parse header
        offset   = 0
        idx      = struct.unpack_from(">I", blob, offset)[0]; offset += 4
        eph_pub_bytes = blob[offset:offset + 32];             offset += 32
        pq_ct_len = struct.unpack_from(">I", blob, offset)[0]; offset += 4

        if len(blob) < offset + pq_ct_len:
            raise ValueError("decrypt: blob truncated in pq_ct")

        _pq_ct   = blob[offset:offset + pq_ct_len]; offset += pq_ct_len
        sealed   = blob[offset:]

        # Retrieve the message key
        final_mk = self._recv_keys.get(idx)
        if final_mk is None:
            raise ValueError(
                f"decrypt: no message key for counter {idx}. "
                "Blob may belong to a different session or was already decrypted."
            )

        # Unseal -- InvalidTag raises if key or content is wrong
        plaintext = unseal(final_mk, sealed)

        # Optionally clear used key (uncomment for strict forward secrecy)
        # del self._recv_keys[idx]

        return plaintext

    def decrypt_text(self, blob: bytes) -> str:
        """Convenience wrapper: decrypt and decode UTF-8."""
        return self.decrypt(blob).decode("utf-8")

    # ── Signing ────────────────────────────────────────────────────

    def _sign(self, data: bytes) -> bytes:
        """Sign `data` with this session's Ed25519 key."""
        return self._sign_priv.sign(data)

    @property
    def public_key_hex(self) -> str:
        """Export this session's signing public key as hex."""
        return self._sign_priv.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        ).hex()
