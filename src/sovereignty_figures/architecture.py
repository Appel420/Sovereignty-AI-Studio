from __future__ import annotations

from dataclasses import dataclass, field

from .validate import validate_thrust

_KNOWN_PATHS = frozenset({"nozzle", "vent", "open_face", "external_coupling"})


@dataclass
class ArchitectureConfig:
    sealed: bool = True
    exhaust_paths: list[str] = field(default_factory=list)

    def declared_exhaust_path(self) -> bool:
        return bool(self.exhaust_paths)

    def is_open_momentum_path(self) -> bool:
        return (not self.sealed) and self.declared_exhaust_path()

    def validate_architecture(self) -> None:
        unknown = set(self.exhaust_paths) - _KNOWN_PATHS
        if unknown:
            raise ValueError(
                f"Unknown exhaust path(s): {sorted(unknown)}. "
                f"Allowed: {sorted(_KNOWN_PATHS)}."
            )

        if self.sealed and self.exhaust_paths:
            raise ValueError(
                "Architecture is not momentum-admissible: sealed=True contradicts declared exhaust path."
            )
        if not self.exhaust_paths:
            raise ValueError(
                "Architecture is not momentum-admissible: no exhaust path declared."
            )


def validate_full(P_watts, eta, Isp_s, arch: ArchitectureConfig, tol=1e-9):
    arch.validate_architecture()
    return validate_thrust(P_watts, eta, Isp_s, tol=tol)
