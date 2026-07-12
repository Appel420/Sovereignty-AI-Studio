#!/usr/bin/env python3
"""Generate credentials for the repository-owned OAuth issuer without network access.

Artifact layout (written to --output-dir):
  oauth-client.json      – client metadata and public JWKS; no private key material
  oauth-private-key.pem  – PKCS#8 PEM private key; permissions 0600
  provenance.json        – immutable generation event record

Compatibility note (v0.2):
  * 'private_key' is no longer stored in oauth-client.json; use oauth-private-key.pem instead.
  * oauth-client.json now includes 'key_reference' and a deterministic 'kid'.
  * Report now uses 'validation', 'generation', 'persistence' fields instead of 'status'.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

if TYPE_CHECKING:
    pass


TOOL_VERSION = "0.2"
PRIVATE_KEY_FILENAME = "oauth-private-key.pem"
SERVICE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def b64url(value: bytes) -> str:
    """Base64url-encode *value* without padding."""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def canonical_json(value: object) -> str:
    """Return a deterministic JSON string with sorted keys and 2-space indent.

    Serialization policy: sort_keys=True, indent=2, separators=(',', ': ').
    All generated JSON files use this function to ensure reproducibility.
    """
    return json.dumps(value, sort_keys=True, indent=2, separators=(",", ": ")) + "\n"


def derive_kid(public_key_bytes: bytes) -> str:
    """Derive a stable key identifier from raw Ed25519 public key bytes.

    Algorithm: SHA-256(raw_public_key_bytes), lower-hex, first 32 characters.
    This is deterministic: anyone holding the public key can recompute the kid.
    """
    return hashlib.sha256(public_key_bytes).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Phase 1 – Validate CLI input
# ---------------------------------------------------------------------------


def validate_service(service: str) -> None:
    """Raise ValueError if *service* does not match the allowed identifier pattern."""
    if not SERVICE_PATTERN.fullmatch(service):
        raise ValueError(
            "service must contain only lowercase letters, digits, underscores, and hyphens"
        )


# ---------------------------------------------------------------------------
# Phase 2 – Canonicalize configuration
# ---------------------------------------------------------------------------


def canonicalize_config(service: str) -> dict:
    """Return a stable, serializable configuration record for *service*."""
    return {
        "issuer": "local",
        "service": service,
        "signing_algorithm": "Ed25519",
        "tool_version": TOOL_VERSION,
    }


# ---------------------------------------------------------------------------
# Phase 3 – Generate key material
# ---------------------------------------------------------------------------


def generate_key_material() -> tuple[Ed25519PrivateKey, bytes, str, str]:
    """Generate an Ed25519 key pair and associated identifiers.

    Returns:
        (private_key, public_key_bytes, kid, client_id)
    """
    private_key = Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    kid = derive_kid(public_key_bytes)
    client_id = f"sg_{secrets.token_urlsafe(18)}"
    return private_key, public_key_bytes, kid, client_id


# ---------------------------------------------------------------------------
# Phase 4 – Policy gate
# ---------------------------------------------------------------------------


def policy_gate(config: dict) -> None:
    """Assert local policy constraints before credential generation proceeds.

    Enforces:
    - signing_algorithm must be in the approved set (currently only Ed25519).
    - issuer must be 'local'; network issuers are not permitted.
    """
    approved_algorithms = {"Ed25519"}
    if config.get("signing_algorithm") not in approved_algorithms:
        raise ValueError(
            f"signing_algorithm must be one of {approved_algorithms}; "
            f"got {config.get('signing_algorithm')!r}"
        )
    if config.get("issuer") != "local":
        raise ValueError("issuer must be 'local'; network issuers are not permitted")


# ---------------------------------------------------------------------------
# Phase 5 – Create provenance
# ---------------------------------------------------------------------------


def create_provenance(service: str, kid: str) -> dict:
    """Return an immutable credential-generation event record (RFC-0007)."""
    return {
        "algorithm": "Ed25519",
        "event": "credential_generated",
        "kid": kid,
        "service": service,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "tool_version": TOOL_VERSION,
    }


# ---------------------------------------------------------------------------
# Phase 6 – Persist artifacts
# ---------------------------------------------------------------------------


def write_json_exclusive(path: Path, value: dict, mode: int) -> None:
    """Write *value* as canonical JSON to *path* with O_EXCL (no-overwrite).

    Raises FileExistsError if *path* already exists.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, mode)
    except FileExistsError:
        raise FileExistsError(
            f"Output file already exists: {path}. "
            "Remove it or choose a different --output-dir."
        )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(canonical_json(value))


def write_pem_exclusive(path: Path, pem_bytes: bytes, mode: int) -> None:
    """Write PEM bytes to *path* with O_EXCL (no-overwrite) and *mode* permissions.

    Raises FileExistsError if *path* already exists.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, mode)
    except FileExistsError:
        raise FileExistsError(
            f"Output file already exists: {path}. "
            "Remove it or choose a different --output-dir."
        )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(pem_bytes)


def persist_artifacts(
    output_dir: Path,
    private_key: Ed25519PrivateKey,
    public_key_bytes: bytes,
    kid: str,
    client_id: str,
    service: str,
    provenance: dict,
) -> None:
    """Write credential artifacts to *output_dir*.

    Files written:
      oauth-client.json      – metadata + public JWKS (no private key material)
      oauth-private-key.pem  – PKCS#8 PEM private key (mode 0600)
      provenance.json        – generation event record

    Uses O_EXCL on each file; raises FileExistsError on collision.
    The output directory must already exist and be writable.
    """
    metadata = {
        "client_id": client_id,
        "client_secret": secrets.token_urlsafe(48),
        "issuer": "local",
        "jwks": {
            "keys": [
                {
                    "alg": "EdDSA",
                    "crv": "Ed25519",
                    "kid": kid,
                    "kty": "OKP",
                    "use": "sig",
                    "x": b64url(public_key_bytes),
                }
            ]
        },
        "key_reference": PRIVATE_KEY_FILENAME,
        "kid": kid,
        "service": service,
    }

    pem_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    write_json_exclusive(output_dir / "oauth-client.json", metadata, 0o600)
    write_pem_exclusive(output_dir / PRIVATE_KEY_FILENAME, pem_bytes, 0o600)
    write_json_exclusive(output_dir / "provenance.json", provenance, 0o600)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _emit_report(report: dict, report_path: Path | None) -> None:
    """Write the report as canonical JSON to *report_path* or stdout."""
    encoded = canonical_json(report)
    if report_path:
        report_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        report_path.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", default="sovereignty-ai-studio")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report: dict = {
        "issuer": "local",
        "network_accessed": False,
        "service": args.service,
        "signing_algorithm": "Ed25519",
    }

    # Phase 1: Validate
    try:
        validate_service(args.service)
    except ValueError as exc:
        parser.error(str(exc))

    if not args.dry_run and args.output_dir is None:
        parser.error("--output-dir is required unless --dry-run is used")

    report["validation"] = "PASS"

    if args.dry_run:
        report["dry_run"] = True
        report["generation"] = "SKIPPED"
        report["persistence"] = "SKIPPED"
        _emit_report(report, args.report)
        return 0

    # Phase 2: Canonicalize config
    config = canonicalize_config(args.service)

    # Phase 3: Generate key material
    try:
        private_key, public_key_bytes, kid, client_id = generate_key_material()
    except Exception as exc:
        report["generation"] = "FAIL"
        report["generation_error"] = str(exc)
        _emit_report(report, args.report)
        return 1

    # Phase 4: Policy gate
    try:
        policy_gate(config)
    except ValueError as exc:
        report["generation"] = "FAIL"
        report["policy_error"] = str(exc)
        _emit_report(report, args.report)
        return 1

    report["generation"] = "PASS"
    report["kid"] = kid

    # Phase 5: Provenance
    provenance = create_provenance(args.service, kid)

    # Phase 6: Persist
    output_dir = args.output_dir.resolve()
    try:
        output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    except FileExistsError:
        report["persistence"] = "FAIL"
        report["persistence_error"] = f"Output directory already exists: {output_dir}"
        _emit_report(report, args.report)
        return 1

    try:
        persist_artifacts(
            output_dir,
            private_key,
            public_key_bytes,
            kid,
            client_id,
            args.service,
            provenance,
        )
        report["output_dir"] = str(output_dir)
        report["persistence"] = "PASS"
        report["provenance_file"] = str(output_dir / "provenance.json")
    except FileExistsError as exc:
        report["persistence"] = "FAIL"
        report["persistence_error"] = str(exc)
        _emit_report(report, args.report)
        return 1
    except OSError as exc:
        report["persistence"] = "FAIL"
        report["persistence_error"] = f"OS error during persistence: {exc}"
        _emit_report(report, args.report)
        return 1

    _emit_report(report, args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
