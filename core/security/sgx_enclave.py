"""SGX enclave compatibility helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SGXEnclave:
    enclave_id: str = "sgx-enclave"
    active: bool = False

    def enter(self) -> None:
        self.active = True

    def exit(self) -> None:
        self.active = False

    def __enter__(self) -> "SGXEnclave":
        self.enter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.exit()