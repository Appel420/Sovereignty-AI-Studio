from __future__ import annotations

from importlib import import_module, util
import json
import os
import re
import secrets
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_jsonschema_spec = util.find_spec("jsonschema")
if _jsonschema_spec is not None:
    _jsonschema = import_module("jsonschema")
    Draft202012Validator = _jsonschema.Draft202012Validator
    FormatChecker = _jsonschema.FormatChecker
else:
    Draft202012Validator = None
    FormatChecker = None

SCHEMA_VERSION = "1.0.0"
ALLOWED_PROFILES = {"personal", "team", "enterprise", "community", "custom"}
REQUIRED_GOVERNANCE = {
    "authorization": "owner-controlled",
    "promotion": "owner-controlled",
    "audit": "mandatory",
    "transparency": "mandatory",
}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,}$")


class ProfileError(Exception):
    """Base deployment-profile error."""


class ValidationError(ProfileError):
    """Validation failure; activation must remain blocked."""


class IsolationError(ProfileError):
    """Deployment isolation failure."""


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
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)


def _new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_hex(16)}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalise_path(path: str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def generate_fresh_profile(*, owner_ref: str, profile_type: str, production_branch: str, integration_branch: str, base_vault_dir: str, development_lanes: list[str] | None = None, agents: list[str] | None = None, providers: list[str] | None = None, local_execution: bool = True, external_execution: bool = False, communication: bool = False, persistence: bool = True, reference_only: bool = False) -> DeploymentProfile:
    """Generate an isolated deployment profile."""
    if profile_type not in ALLOWED_PROFILES:
        raise ValidationError(f"invalid profile type: {profile_type}")
    if not isinstance(owner_ref, str) or len(owner_ref) < 8:
        raise ValidationError("owner_ref must be an opaque local reference of at least 8 characters")
    if "@" in owner_ref:
        raise ValidationError("owner_ref must not be email-like")
    if not production_branch or not integration_branch:
        raise ValidationError("production_branch and integration_branch are required")
    if not isinstance(base_vault_dir, str) or not base_vault_dir.strip():
        raise ValidationError("base_vault_dir is required")
    base_root = _normalise_path(base_vault_dir)
    deployment_id = _new_id("dep_")
    instance_root = base_root / deployment_id
    state_path = instance_root / "state"
    evidence_path = instance_root / "evidence"
    if _normalise_path(str(state_path)) == _normalise_path(str(evidence_path)):
        raise IsolationError("generated state and evidence paths collide")
    return DeploymentProfile(
        deployment=DeploymentSection(id=deployment_id, profile=profile_type, created_at=_utc_now(), reference_only=reference_only),
        identity=IdentitySection(owner_ref=owner_ref, device_id=_new_id("dev_"), authority_id=_new_id("auth_")),
        vault=VaultSection(state_path=str(state_path), memory_scope="instance-local", evidence_path=str(evidence_path)),
        topology=TopologySection(production_branch=production_branch, integration_branch=integration_branch, development_lanes=list(development_lanes or []), agents=list(agents or []), providers=list(providers or [])),
        capabilities=CapabilitiesSection(local_execution=local_execution, external_execution=external_execution, communication=communication, persistence=persistence),
        governance=GovernanceSection(),
    )


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object": return isinstance(value, dict)
    if expected == "array": return isinstance(value, list)
    if expected == "string": return isinstance(value, str)
    if expected == "boolean": return isinstance(value, bool)
    if expected == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number": return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null": return value is None
    return False


def _minimal_schema_errors(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    if not isinstance(schema, dict): return [f"{path}: schema node must be an object"]
    errors: list[str] = []
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _type_matches(value, expected_type): return [f"{path}: expected {expected_type}"]
    if "const" in schema and value != schema["const"]: errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]: errors.append(f"{path}: must be one of {schema['enum']!r}")
    if isinstance(value, str):
        minimum = schema.get("minLength")
        if minimum is not None:
            try: minimum = int(minimum)
            except (TypeError, ValueError): return [f"{path}: invalid minLength in schema"]
            if len(value) < minimum: errors.append(f"{path}: shorter than minimum length {minimum}")
        if schema.get("format") == "date-time":
            try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError: errors.append(f"{path}: invalid RFC3339 date-time")
            else:
                if parsed.tzinfo is None: errors.append(f"{path}: date-time must include timezone information")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not isinstance(properties, dict): return [f"{path}: schema properties must be an object"]
        required = schema.get("required", [])
        if not isinstance(required, list): return [f"{path}: schema required must be an array"]
        for name in required:
            if name not in value: errors.append(f"{path}: missing required property {name!r}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties: errors.append(f"{path}: additional property {key!r} is not allowed")
        for key, child_schema in properties.items():
            if key not in value: continue
            if not isinstance(child_schema, dict): return [f"{path}.{key}: child schema must be an object"]
            errors.extend(_minimal_schema_errors(value[key], child_schema, f"{path}.{key}"))
    if isinstance(value, list):
        if schema.get("uniqueItems") is True:
            try: serialised = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            except (TypeError, ValueError) as exc: return [f"{path}: cannot evaluate uniqueItems: {exc}"]
            if len(serialised) != len(set(serialised)): errors.append(f"{path}: array items must be unique")
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, dict): return [f"{path}: item schema must be an object"]
            for index, item in enumerate(value): errors.extend(_minimal_schema_errors(item, item_schema, f"{path}[{index}]"))
    return errors


def _validate_schema_contract(instance: dict[str, Any], schema: Any) -> list[str]:
    if not isinstance(schema, dict): return ["schema invalid: schema must be an object"]
    if schema.get("type") != "object": return ["schema invalid: deployment profile schema must be an object schema"]
    if Draft202012Validator is not None and FormatChecker is not None:
        try:
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            errors: list[str] = []
            for error in validator.iter_errors(instance):
                if error.validator == "additionalProperties":
                    unexpected = sorted(error.validator_value if isinstance(error.validator_value, list) else [])
                    if unexpected:
                        errors.append("additional property " + ", ".join(repr(name) for name in unexpected) + " is not allowed")
                    else:
                        errors.append("additional property is not allowed")
                else:
                    errors.append(error.message)
            return errors
        except Exception as exc:
            return [f"schema invalid: {exc}"]
    return _minimal_schema_errors(instance, schema)


def validate_profile(profile: DeploymentProfile, schema_path: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(profile, DeploymentProfile): return ["profile must be a DeploymentProfile"]
    schema_path = Path(schema_path)
    try: schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc: return [f"schema unavailable: {exc}"]
    schema_errors = _validate_schema_contract(profile.to_dict(), schema)
    if schema_errors: errors.extend(schema_errors)
    if profile.deployment.schema_version != SCHEMA_VERSION: errors.append(f"deployment.schema_version must equal {SCHEMA_VERSION!r}")
    if profile.deployment.reference_only: errors.append("reference_only profile cannot be activated")
    for name, value in (("owner_ref", profile.identity.owner_ref), ("device_id", profile.identity.device_id), ("authority_id", profile.identity.authority_id)):
        if not isinstance(value, str) or len(value) < 8: errors.append(f"identity.{name} is missing or too short")
        if "@" in value: errors.append(f"identity.{name} contains an email-like identifier")
    if not isinstance(profile.identity.key_refs, list): errors.append("identity.key_refs must be a list")
    elif len(profile.identity.key_refs) != len(set(profile.identity.key_refs)): errors.append("identity.key_refs contains duplicates")
    vault = profile.vault
    if vault.isolation != "strict": errors.append("vault.isolation must be strict")
    if vault.credentials_protected is not True: errors.append("vault.credentials_protected must be true")
    try:
        state_path = _normalise_path(vault.state_path); evidence_path = _normalise_path(vault.evidence_path)
    except (OSError, RuntimeError, ValueError) as exc: errors.append(f"vault path normalization failed: {exc}")
    else:
        if state_path == evidence_path: errors.append("state_path and evidence_path collide")
        if state_path == Path("/") or evidence_path == Path("/"): errors.append("vault paths must not resolve to filesystem root")
    topology = profile.topology
    if not topology.production_branch: errors.append("production branch must be explicit")
    if not topology.integration_branch: errors.append("integration branch must be explicit")
    for name, values in (("development_lanes", topology.development_lanes), ("agents", topology.agents), ("providers", topology.providers)):
        if not isinstance(values, list): errors.append(f"topology.{name} must be a list"); continue
        if len(values) != len(set(values)): errors.append(f"topology.{name} contains duplicates")
    for name in ("local_execution", "external_execution", "communication", "persistence"):
        if not isinstance(getattr(profile.capabilities, name), bool): errors.append(f"capabilities.{name} must be boolean")
    for name, expected in REQUIRED_GOVERNANCE.items():
        if getattr(profile.governance, name) != expected: errors.append(f"governance.{name} must equal {expected!r}")
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
    errors = validate_profile(profile, schema_path)
    steps_completed = ["schema_validation"]
    schema_unavailable = len(errors) == 1 and errors[0].startswith("schema unavailable:")
    if not schema_unavailable: steps_completed.extend(["identity_validation", "vault_isolation_validation", "topology_validation", "capability_validation", "governance_validation"])
    steps_completed.extend(["scar_initialization_required", "owner_approval_required"])
    return ValidationReport(deployment_id=profile.deployment.id, valid=not errors, errors=errors, timestamp=_utc_now(), steps_completed=steps_completed, owner_approval_required=True)


def save_profile(profile: DeploymentProfile, path: str | Path) -> None:
    if not isinstance(profile, DeploymentProfile): raise ValidationError("profile must be a DeploymentProfile")
    destination = Path(path).expanduser()
    if destination.name in {"", ".", ".."}: raise ValidationError("profile destination must be a file path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = profile.to_json() + "\n"
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try: os.unlink(temporary_name)
        except FileNotFoundError: pass
        raise
