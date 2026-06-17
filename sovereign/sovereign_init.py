from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


def _secret() -> bytes:
    return os.environ.get("SOVEREIGN_API_KEY_SECRET", "sovereign-default-secret").encode()


@dataclass(slots=True)
class Sovereign:
    def derive_api_key(self, service_name: str, length: int = 32) -> str:
        digest = hashlib.sha256(_secret() + b":" + service_name.encode()).hexdigest()
        while len(digest) < length * 2:
            digest += hashlib.sha256(digest.encode()).hexdigest()
        return digest[: length * 2]

    def rotate_all(self, rotation_id: str) -> dict[str, object]:
        return {
            "status": "success",
            "rotation_id": rotation_id,
            "rotated": True,
        }


sovereign = Sovereign()


async def init_sovereign() -> dict[str, object]:
    return {"status": "success", "initialized": True}
