from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.coordination.repository_registry import (
    RepositoryContract,
    RepositoryRegistry,
    RepositoryRegistryError,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "integration" / "repository-registry.json"
SCHEMA_PATH = ROOT / "schemas" / "repository-contract.schema.json"


def test_registry_is_valid_json_and_declares_schema() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert registry["schema_version"] == "1.0"
    assert registry["registry_id"] == "sovereignty-repository-topology"
    assert schema["$id"] == "sovereignty://schemas/repository-contract.schema.json"
    assert schema["properties"]["repositories"]["items"]["$ref"] == "#/$defs/repository"


def test_registry_loads_without_duplicate_ids_or_unknown_dependencies() -> None:
    registry = RepositoryRegistry.load(REGISTRY_PATH)

    assert registry.get("sovereignty-ai-gate") is not None
    assert registry.get("sovereignty-ai-studio") is not None
    assert registry.get("devassist420") is not None
    assert registry.get("hawking-runtime") is not None


def test_studio_is_integration_not_authority() -> None:
    registry = RepositoryRegistry.load(REGISTRY_PATH)

    studio = registry.require("sovereignty-ai-studio")
    gate = registry.require("sovereignty-ai-gate")

    assert studio.authority_domain == "integration"
    assert gate.authority_domain == "authority"
    assert "authorization" in gate.capabilities
    assert "authorization" in studio.consumes_capabilities


def test_hawking_remains_runtime_transport_and_owner_channel() -> None:
    registry = RepositoryRegistry.load(REGISTRY_PATH)
    hawking = registry.require("hawking-runtime")

    assert hawking.authority_domain == "transport"
    assert "hawking-transport" in hawking.capabilities
    assert "mesh-transport" in hawking.capabilities
    assert "owner-channel" in hawking.capabilities
    assert hawking.network == "policy-gated"


def test_ghost_or_runtime_state_is_not_encoded_as_network_shutdown() -> None:
    registry = RepositoryRegistry.load(REGISTRY_PATH)

    studio = registry.require("sovereignty-ai-studio")
    hawking = registry.require("hawking-runtime")

    assert studio.network == "policy-gated"
    assert hawking.network == "policy-gated"


def test_capability_has_single_declared_owner() -> None:
    registry = RepositoryRegistry.load(REGISTRY_PATH)

    gate = registry.resolve_capability("authorization")
    execution = registry.resolve_capability("execution")

    assert gate.id == "sovereignty-ai-gate"
    assert execution.id == "devassist420"


def test_duplicate_capability_owners_fail_closed() -> None:
    entries = (
        RepositoryContract(
            id="a",
            repository="Appel420/a",
            role="test",
            required=False,
            capabilities=frozenset({"shared"}),
            trust_level="test",
            network="disabled",
            authority_domain="research",
            interfaces=(),
            dependencies=frozenset(),
            consumes_capabilities=frozenset(),
        ),
        RepositoryContract(
            id="b",
            repository="Appel420/b",
            role="test",
            required=False,
            capabilities=frozenset({"shared"}),
            trust_level="test",
            network="disabled",
            authority_domain="research",
            interfaces=(),
            dependencies=frozenset(),
            consumes_capabilities=frozenset(),
        ),
    )
    registry = RepositoryRegistry(entries, metadata={})

    with pytest.raises(RepositoryRegistryError, match="multiple owners"):
        registry.resolve_capability("shared")


def test_unknown_capability_produces_unresolved_finding() -> None:
    registry = RepositoryRegistry.load(REGISTRY_PATH)

    finding = registry.route_finding(
        component="Gate One audit",
        capability="does-not-exist",
    )

    assert finding.status == "UNRESOLVED"
    assert finding.owner_repository is None
    assert finding.capability == "does-not-exist"


def test_known_capability_routes_to_owner_repository() -> None:
    registry = RepositoryRegistry.load(REGISTRY_PATH)

    finding = registry.route_finding(
        component="execution adapter",
        capability="execution",
    )

    assert finding.status == "ROUTED"
    assert finding.owner_repository == "Appel420/DevAssist420"
    assert finding.capability == "execution"


def test_missing_required_registry_fields_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "repositories": [{"id": "broken"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RepositoryRegistryError, match="missing fields"):
        RepositoryRegistry.load(path)
