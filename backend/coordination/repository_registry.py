"""Bounded consumer for the cross-repository integration registry.

This module resolves topology and ownership metadata only. It does not grant
authority, issue capabilities, execute operations, or emit SCAR by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "integration" / "repository-registry.json"


class RepositoryRegistryError(ValueError):
    """Raised when the repository topology contract is invalid."""


@dataclass(frozen=True, slots=True)
class RepositoryContract:
    id: str
    repository: str
    role: str
    required: bool
    capabilities: frozenset[str]
    trust_level: str
    network: str
    authority_domain: str
    interfaces: tuple[dict[str, str], ...]
    dependencies: frozenset[str]
    consumes_capabilities: frozenset[str]
    evidence_contract: str | None = None
    attestation_contract: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RepositoryContract":
        required = {
            "id", "repository", "role", "required", "capabilities",
            "trust_level", "network", "authority_domain", "interfaces",
            "dependencies",
        }
        missing = required.difference(value)
        if missing:
            raise RepositoryRegistryError(
                f"repository entry missing fields: {sorted(missing)}"
            )
        entry_id = str(value.get("id", "<unknown>"))
        required_value = value["required"]
        if not isinstance(required_value, bool):
            raise RepositoryRegistryError(
                f"repository entry {entry_id} field 'required' must be boolean"
            )
        try:
            interfaces = tuple(
                {"name": str(item["name"]), "kind": str(item["kind"])}
                for item in value["interfaces"]
            )
        except (TypeError, KeyError) as exc:
            raise RepositoryRegistryError(
                f"repository entry {entry_id} has invalid interfaces: {exc}"
            ) from exc
        try:
            capabilities = frozenset(map(str, value["capabilities"]))
            dependencies = frozenset(map(str, value["dependencies"]))
            consumes = frozenset(map(str, value.get("consumes_capabilities", [])))
        except TypeError as exc:
            raise RepositoryRegistryError(
                f"repository entry {entry_id} has invalid list fields: {exc}"
            ) from exc
        return cls(
            id=entry_id,
            repository=str(value["repository"]),
            role=str(value["role"]),
            required=required_value,
            capabilities=capabilities,
            trust_level=str(value["trust_level"]),
            network=str(value["network"]),
            authority_domain=str(value["authority_domain"]),
            interfaces=interfaces,
            dependencies=dependencies,
            consumes_capabilities=consumes,
            evidence_contract=value.get("evidence_contract"),
            attestation_contract=value.get("attestation_contract"),
        )


@dataclass(frozen=True, slots=True)
class IntegrationFinding:
    """A topology finding, not an authorization decision."""

    component: str
    owner_repository: str | None
    capability: str | None
    status: str
    reason: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "component": self.component,
            "owner_repository": self.owner_repository,
            "capability": self.capability,
            "status": self.status,
            "reason": self.reason,
        }


class RepositoryRegistry:
    def __init__(self, repositories: tuple[RepositoryContract, ...], *, metadata: Mapping[str, Any]) -> None:
        self._repositories = {item.id: item for item in repositories}
        self.metadata = dict(metadata)
        if len(self._repositories) != len(repositories):
            raise RepositoryRegistryError("duplicate repository id")

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY_PATH) -> "RepositoryRegistry":
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepositoryRegistryError(f"cannot load registry: {exc}") from exc

        if not isinstance(document, dict):
            raise RepositoryRegistryError("registry document must be a JSON object")

        required_fields = {
            "schema_version",
            "registry_id",
            "registry_revision_id",
            "status",
            "repositories",
        }
        missing = required_fields.difference(document)
        if missing:
            raise RepositoryRegistryError(f"registry missing fields: {sorted(missing)}")

        if document.get("schema_version") != "1.0":
            raise RepositoryRegistryError("unsupported registry schema_version")
        repositories = tuple(
            RepositoryContract.from_mapping(item)
            for item in document.get("repositories", [])
        )
        if not repositories:
            raise RepositoryRegistryError("registry contains no repositories")

        ids = {item.id for item in repositories}
        for item in repositories:
            unknown = item.dependencies.difference(ids)
            if unknown:
                raise RepositoryRegistryError(
                    f"{item.id} references unknown dependencies: {sorted(unknown)}"
                )
        return cls(repositories, metadata=document)

    def get(self, repository_id: str) -> RepositoryContract | None:
        return self._repositories.get(repository_id)

    def require(self, repository_id: str) -> RepositoryContract:
        repository = self.get(repository_id)
        if repository is None:
            raise RepositoryRegistryError(f"unknown repository: {repository_id}")
        return repository

    def owners_of(self, capability: str) -> tuple[RepositoryContract, ...]:
        return tuple(
            sorted(
                (item for item in self._repositories.values() if capability in item.capabilities),
                key=lambda item: item.id,
            )
        )

    def resolve_capability(self, capability: str) -> RepositoryContract:
        owners = self.owners_of(capability)
        if not owners:
            raise RepositoryRegistryError(f"no repository owns capability: {capability}")
        if len(owners) > 1:
            raise RepositoryRegistryError(
                f"capability has multiple owners: {capability}: {[item.id for item in owners]}"
            )
        return owners[0]

    def resolve_interface(self, name: str) -> RepositoryContract:
        matches = tuple(
            item for item in self._repositories.values()
            if any(interface["name"] == name for interface in item.interfaces)
        )
        if not matches:
            raise RepositoryRegistryError(f"no repository owns interface: {name}")
        if len(matches) > 1:
            raise RepositoryRegistryError(
                f"interface has multiple owners: {name}: {[item.id for item in matches]}"
            )
        return matches[0]

    def route_finding(self, *, component: str, capability: str | None = None) -> IntegrationFinding:
        if capability is None:
            return IntegrationFinding(
                component=component,
                owner_repository=None,
                capability=None,
                status="UNRESOLVED",
                reason="no capability supplied",
            )
        try:
            owner = self.resolve_capability(capability)
        except RepositoryRegistryError as exc:
            return IntegrationFinding(
                component=component,
                owner_repository=None,
                capability=capability,
                status="UNRESOLVED",
                reason=str(exc),
            )
        return IntegrationFinding(
            component=component,
            owner_repository=owner.repository,
            capability=capability,
            status="ROUTED",
            reason="capability ownership resolved from registry",
        )

    def repositories(self) -> tuple[RepositoryContract, ...]:
        return tuple(sorted(self._repositories.values(), key=lambda item: item.id))


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "IntegrationFinding",
    "RepositoryContract",
    "RepositoryRegistry",
    "RepositoryRegistryError",
]
