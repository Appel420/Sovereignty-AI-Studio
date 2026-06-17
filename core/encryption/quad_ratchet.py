"""Compatibility ratchet session helpers."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(data: str | bytes) -> bytes:
    return base64.b64decode(data)


def _derive_key(root_key: bytes, counter: int) -> bytes:
    material = root_key + counter.to_bytes(8, "big", signed=False)
    return hashlib.sha256(material).digest()


@dataclass
class QuadRatchetSession:
    session_id: str = field(default_factory=lambda: secrets.token_hex(16))
    root_key: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    send_counter: int = 0
    recv_counter: int = 0

    def seal(self, payload: bytes | str, aad: bytes | str = b"") -> dict[str, Any]:
        plaintext = payload.encode() if isinstance(payload, str) else bytes(payload)
        associated_data = aad.encode() if isinstance(aad, str) else bytes(aad)
        counter = self.send_counter
        nonce = secrets.token_bytes(12)
        key = _derive_key(self.root_key, counter)
        ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext, associated_data)
        self.send_counter += 1
        return {
            "session_id": self.session_id,
            "counter": counter,
            "nonce": _b64(nonce),
            "ciphertext": _b64(ciphertext),
        }

    def unseal(self, payload: dict[str, Any], aad: bytes | str = b"") -> bytes:
        associated_data = aad.encode() if isinstance(aad, str) else bytes(aad)
        counter = int(payload["counter"])
        key = _derive_key(self.root_key, counter)
        plaintext = ChaCha20Poly1305(key).decrypt(
            _unb64(payload["nonce"]),
            _unb64(payload["ciphertext"]),
            associated_data,
        )
        self.recv_counter = max(self.recv_counter, counter + 1)
        return plaintext

    def advance(self) -> None:
        self.send_counter += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "root_key": _b64(self.root_key),
            "send_counter": self.send_counter,
            "recv_counter": self.recv_counter,
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> "QuadRatchetSession":
        return cls(
            session_id=str(snapshot["session_id"]),
            root_key=_unb64(str(snapshot["root_key"])),
            send_counter=int(snapshot.get("send_counter", 0)),
            recv_counter=int(snapshot.get("recv_counter", 0)),
        )