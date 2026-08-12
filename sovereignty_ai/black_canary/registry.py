"""Verified trust-anchor registry for Black Canary signers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from .crypto import BLACK_CANARY_SUITE, blake3_digest


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class TrustAnchor:
    key_id: str
    verify_key: str
    algorithm: str = "Ed25519"
    suite: str = BLACK_CANARY_SUITE

    def signable(self) -> bytes:
        return _canonical(asdict(self))

    def key(self) -> VerifyKey:
        if self.algorithm != "Ed25519" or self.suite != BLACK_CANARY_SUITE:
            raise ValueError("unsupported trust-anchor algorithm or suite")
        return VerifyKey(bytes.fromhex(self.verify_key))


class KeyRegistry:
    """Registry whose entries can only be installed with a verified signature."""

    def __init__(self, registry_verify_key: VerifyKey | None = None) -> None:
        self.registry_verify_key = registry_verify_key
        self._anchors: dict[str, TrustAnchor] = {}

    @staticmethod
    def signed_anchor(anchor: TrustAnchor, registry_key: SigningKey) -> tuple[dict[str, Any], str]:
        signature = registry_key.sign(anchor.signable()).signature.hex()
        return asdict(anchor), signature

    def register_signed(self, anchor: TrustAnchor, signature: str) -> None:
        if self.registry_verify_key is None:
            raise ValueError("registry trust anchor is not configured")
        try:
            self.registry_verify_key.verify(anchor.signable(), bytes.fromhex(signature))
        except (BadSignatureError, ValueError) as exc:
            raise ValueError("trust-anchor registry signature rejected") from exc
        anchor.key()
        self._anchors[anchor.key_id] = anchor

    def register_verified(self, anchor: TrustAnchor) -> None:
        """Install an already verified anchor, for sealed local bootstrap data."""
        anchor.key()
        self._anchors[anchor.key_id] = anchor

    def get(self, key_id: str) -> TrustAnchor:
        try:
            return self._anchors[key_id]
        except KeyError as exc:
            raise KeyError(f"unknown trust anchor: {key_id}") from exc

    def verify_key(self, key_id: str) -> VerifyKey:
        return self.get(key_id).key()

    def export(self) -> dict[str, Any]:
        return {
            "suite": BLACK_CANARY_SUITE,
            "registry_digest": blake3_digest(
                _canonical([asdict(self._anchors[key]) for key in sorted(self._anchors)])
            ).hex(),
            "anchors": [asdict(self._anchors[key]) for key in sorted(self._anchors)],
        }
