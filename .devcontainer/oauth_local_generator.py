#!/usr/bin/env python3
"""Generate credentials for the repository-owned OAuth issuer without network access."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


SERVICE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def write_json(path: Path, value: dict, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, mode)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", default="sovereignty-ai-studio")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    if not SERVICE_PATTERN.fullmatch(args.service):
        parser.error("service must contain only lowercase letters, digits, underscores, and hyphens")
    if not args.dry_run and args.output_dir is None:
        parser.error("--output-dir is required unless --dry-run is used")

    report = {
        "status": "validated" if args.dry_run else "generated",
        "service": args.service,
        "issuer": "local",
        "network_accessed": False,
        "signing_algorithm": "Ed25519",
    }
    if not args.dry_run:
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        credentials = {
            "client_id": f"sg_{secrets.token_urlsafe(18)}",
            "client_secret": secrets.token_urlsafe(48),
            "service": args.service,
            "issuer": "local",
            "jwks": {
                "keys": [{
                    "kty": "OKP",
                    "crv": "Ed25519",
                    "alg": "EdDSA",
                    "use": "sig",
                    "kid": secrets.token_hex(8),
                    "x": b64url(public_key),
                }]
            },
            "private_key": b64url(private_key.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )),
        }
        write_json(output_dir / "oauth-client.json", credentials, 0o600)
        report["output_dir"] = str(output_dir)

    encoded_report = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        args.report.write_text(encoded_report, encoding="utf-8")
    else:
        sys.stdout.write(encoded_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
