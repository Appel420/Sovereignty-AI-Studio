from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "1.0.0"
ALLOWED_PROFILES = {"personal", "team", "enterprise", "community", "custom"}
REQUIRED_GOVERNANCE = {
    "authorization": "owner-controlled",
    "promotion": "owner-controlled",
    "audit": "mandatory",
    "transparency": "mandatory",
}


class ProfileError(Exception):
    """Base deployment-profile error."""


class ValidationError(ProfileError):
    """Raised when validation fails; activation must remain blocked."""


class IsolationError(ProfileError):
    """Raised when deployment isolation cannot be established."""


@dataclass(frozen=True)
class DeploymentSection:
    id: str
    profile: str
    created_at: str
    schema_version: str = SCHEMA_VERSION
    reference_only: bool = False


@dataclass(frozen=True)
class IdentitySection:
    owner_ref: str
    device_id: str
    authority_id: str
    key_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VaultSection:
    state_path: str
    memory_scope: str
    evidence_path: str
    isolation: str = "strict"
    credentials_protected: bool = True


@dataclass(frozen=True)
class TopologySection:
    production_branch: str
    integration_branch: str
    development_lanes: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CapabilitiesSection:
    local_execution: bool
    external_execution: bool
    communication: bool
    persistence: bool


@dataclass(frozen=True)
class GovernanceSection:
    authorization: str = "owner-controlled"
    promotion: str = "owner-controlled"
    audit: str = "mandatory"
    transparency: str = "mandatory"


@dataclass(frozen=True)
class DeploymentProfile:
    deployment: DeploymentSection
    identity: IdentitySection
    vault: VaultSection
    topology: TopologySection
    capabilities: CapabilitiesSection
    governance: GovernanceSection

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def _id(prefix: str) -> str:
    return f"{prefix}{secrets.token_hex(16)}"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def generate_fresh_profile(
    *,
    owner_ref: str,
    profile_type: str,
    production_branch: str,
    integration_branch: str,
    base_vault_dir: str,
    development_lanes: list[str] | None = None,
    agents: list[str] | None = None,
    providers: list[str] | None = None,
    local_execution: bool = True,
    external_execution: bool = False,
    communication: bool = False,
    persistence: bool = True,
    reference_only: bool = False,
) -> DeploymentProfile:
    """Create a profile from explicit installation inputs; no topology defaults."""
    if profile_type not in ALLOWED_PROFILES:
        raise ValidationError(f"invalid profile type: {profile_type}")
    if len(owner_ref) < 8:
        raise ValidationError("owner_ref must be an opaque local reference of at least 8 characters")
    if not production_branch or not integration_branch:
        raise ValidationError("production_branch and integration_branch must be explicit")

    deployment_id = _id("dep_")
    instance_root = Path(base_vault_dir).expanduser() / deployment_id

    return DeploymentProfile(
        deployment=DeploymentSection(deployment_id, profile_type, _utc_now(), reference_only=reference_only),
        identity=IdentitySection(owner_ref, _id("dev_"), _id("auth_")),
        vault=VaultSection(str(instance_root / "state"), "instance-local", str(instance_root / "evidence")),
        topology=TopologySection(
            production_branch,
            integration_branch,
            list(development_lanes or []),
            list(agents or []),
            list(providers or []),
        ),
        capabilities=CapabilitiesSection(local_execution, external_execution, communication, persistence),
        governance=GovernanceSection(),
    )


def validate_profile(profile: DeploymentProfile, schema_path: Path) -> list[str]:
    """Run structural, identity, isolation, topology, capability, and governance checks."""
    errors: list[str] = []
    document = profile.to_dict()

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"schema unavailable: {exc}"]

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors.extend(error.message for error in validator.iter_errors(document))

    if profile.deployment.reference_only:
        errors.append("reference_only profiles cannot be activated")

    identity = profile.identity
    for name, value in (("owner_ref", identity.owner_ref), ("device_id", identity.device_id), ("authority_id", identity.authority_id)):
        if not value or len(value) < 8:
            errors.append(f"identity.{name} is missing or too short")
        if "@" in value:
            errors.append(f"identity.{name} contains an email-like identifier")

    vault = profile.vault
    if vault.isolation != "strict":
        errors.append("vault isolation is not strict")
    if vault.credentials_protected is not True:
        errors.append("vault credentials are not protected")
    if Path(vault.state_path) == Path(vault.evidence_path):
        errors.append("state and evidence paths collide")

    topology = profile.topology
    if not topology.production_branch or not topology.integration_branch:
        errors.append("production and integration branches must be explicit")
    for name, values in (("development_lanes", topology.development_lanes), ("agents", topology.agents), ("providers", topology.providers)):
        if len(values) != len(set(values)):
            errors.append(f"topology.{name} contains duplicates")

    for name in ("local_execution", "external_execution", "communication", "persistence"):
        if not isinstance(getattr(profile.capabilities, name), bool):
            errors.append(f"capabilities.{name} must be boolean")

    for name, expected in REQUIRED_GOVERNANCE.items():
        if getattr(profile.governance, name) != expected:
            errors.append(f"governance.{name} must equal {expected!r}")

    return errors


@dataclass(frozen=True)
class ValidationReport:
    deployment_id: str
    valid: bool
    errors: list[str]
    timestamp: str
    steps_completed: list[str]
    owner_approval_required: bool = True


def run_validation_pipeline(profile: DeploymentProfile, schema_path: Path) -> ValidationReport:
    """Validate without activation; owner approval remains a separate boundary."""
    errors = validate_profile(profile, schema_path)
    steps = [
        "schema_validation",
        "identity_validation",
        "vault_isolation_validation",
        "topology_validation",
        "capability_validation",
        "governance_validation",
        "scar_initialization_required",
        "owner_approval_required",
    ]
    return ValidationReport(profile.deployment.id, not errors, errors, _utc_now(), steps)


def save_profile(profile: DeploymentProfile, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(profile.to_json(), encoding="utf-8")
