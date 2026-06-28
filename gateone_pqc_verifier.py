#!/usr/bin/env python3
"""
GATEONE PQC Verifier — production attestation service.

Ports are resolved through ConfigFixer defaults so deployment can override
them via environment without hard-coding runtime values in the service.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fixers.config_fixer import ConfigFixer

try:
    import oqs  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    oqs = None

try:
    from core.security.tpm_attestation import TPMAttester
except ImportError:  # pragma: no cover - optional dependency

    class TPMAttester:  # type: ignore[override]
        def attest(self):
            return type("AttestationResult", (), {"verified": False, "details": {"status": "not_available"}})()


try:
    from sovereign_vault import SovereignVault
except ImportError:  # pragma: no cover - optional dependency

    class SovereignVault:
        def log_event(self, event: str, data: dict[str, Any]) -> None:
            logging.getLogger("gateone").info("%s %s", event, data)


try:
    from scar_log import ScarLog
except ImportError:  # pragma: no cover - optional dependency

    class ScarLog:
        def __init__(self, path: Path):
            self.path = path

        def append(self, entry: dict[str, Any]) -> None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")


log = logging.getLogger("gateone")

RUNTIME = ConfigFixer(
    defaults={
        "GATEONE_VERIFIER_PORT": 9899,
        "GATEONE_VERIFIER_HOST": "0.0.0.0",
        "GATEONE_KEY_DIR": "/etc/gateone/keys",
        "GATEONE_SCAR_LOG_PATH": "/var/log/gateone_pqc_scar.log",
    }
).fix_env_config()

SIG_ALG = "ML-DSA-87"
VERIFIER_HOST = str(RUNTIME["GATEONE_VERIFIER_HOST"])
VERIFIER_PORT = int(RUNTIME["GATEONE_VERIFIER_PORT"])
KEY_DIR = Path(str(RUNTIME["GATEONE_KEY_DIR"]))
SCAR_LOG_PATH = Path(str(RUNTIME["GATEONE_SCAR_LOG_PATH"]))

KEY_DIR.mkdir(parents=True, exist_ok=True)

VAULT = SovereignVault()
SCAR = ScarLog(SCAR_LOG_PATH)
app = FastAPI(
    title="GATEONE PQC Verifier",
    description="Post-quantum attestation service with explicit evidence output.",
    version="1.0.0",
)


class AttestationToken(BaseModel):
    attestation_token: str = Field(..., description="JSON payload with signature, public_key, and optional tpm_quote")
    max_age_seconds: int = Field(300, ge=60, le=3600)


class AttestationResponse(BaseModel):
    valid: bool
    node_id: Optional[str] = None
    algorithm: Optional[str] = None
    dilithium_valid: Optional[bool] = None
    tpm_valid: Optional[bool] = None
    reason: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


def _log_attestation(event: str, node_id: Optional[str], extra: dict[str, Any] | None = None) -> None:
    entry: dict[str, Any] = {
        "ts": int(time.time()),
        "event": event,
        "node_id": node_id,
        "service": "gateone_pqc_verifier",
    }
    if extra:
        entry.update(extra)
    SCAR.append(entry)
    VAULT.log_event("pqc_attestation", entry)


def _load_signer():
    if oqs is None:
        return None, None, None

    signer = oqs.Signature(SIG_ALG)
    pub_path = KEY_DIR / f"{SIG_ALG}.pub"
    priv_path = KEY_DIR / f"{SIG_ALG}.priv"

    if priv_path.exists() and pub_path.exists():
        private_key = priv_path.read_bytes()
        public_key = pub_path.read_bytes()
        signer.import_secret_key(private_key)
        return signer, public_key, private_key

    public_key = signer.generate_keypair()
    private_key = signer.export_secret_key()
    priv_path.write_bytes(private_key)
    pub_path.write_bytes(public_key)
    priv_path.chmod(0o600)
    return signer, public_key, private_key


SIGNER, PUBLIC_KEY, PRIVATE_KEY = _load_signer()


def _tpm_verified(quote: Optional[dict[str, Any]], nonce: str) -> bool:
    if quote is None:
        return True
    try:
        return bool(TPMAttester().attest().verified)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("TPM attestation failed: %s", exc)
        return False


@app.post("/verify-attestation", response_model=AttestationResponse)
async def verify_attestation(token: AttestationToken):
    try:
        if SIGNER is None or PUBLIC_KEY is None:
            raise HTTPException(status_code=503, detail="oqs-python is required for ML-DSA verification")

        data = json.loads(token.attestation_token)
        payload = data.get("payload", {})
        signature_hex = data.get("signature", "")
        public_key_hex = data.get("public_key", "")
        tpm_quote = data.get("tpm_quote")

        node_id = payload.get("node_id", "unknown")
        age = time.time() - float(payload.get("timestamp", 0))
        if age > token.max_age_seconds:
            _log_attestation("attestation_failed", node_id, {"reason": "token_too_old", "age": age})
            return AttestationResponse(valid=False, reason="token_too_old", node_id=node_id)

        message_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = bytes.fromhex(signature_hex)
        public_key = bytes.fromhex(public_key_hex)
        is_dilithium_valid = SIGNER.verify(message_bytes, signature, public_key)
        is_tpm_valid = _tpm_verified(tpm_quote, str(payload.get("nonce", "")))

        if is_dilithium_valid and is_tpm_valid:
            _log_attestation(
                "attestation_success",
                node_id,
                {"algorithm": SIG_ALG, "dilithium_valid": True, "tpm_valid": is_tpm_valid},
            )
            return AttestationResponse(
                valid=True,
                node_id=node_id,
                algorithm=SIG_ALG,
                dilithium_valid=True,
                tpm_valid=is_tpm_valid,
            )

        _log_attestation(
            "attestation_failed",
            node_id,
            {"dilithium_valid": is_dilithium_valid, "tpm_valid": is_tpm_valid},
        )
        return AttestationResponse(
            valid=False,
            node_id=node_id,
            dilithium_valid=is_dilithium_valid,
            tpm_valid=is_tpm_valid,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        _log_attestation("attestation_error", None, {"error": str(exc)})
        return AttestationResponse(valid=False, reason=str(exc))


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "GATEONE PQC Verifier",
        "algorithm": SIG_ALG,
        "port": VERIFIER_PORT,
        "host": VERIFIER_HOST,
        "keys_persisted": PRIVATE_KEY is not None and PUBLIC_KEY is not None,
        "oqs_available": oqs is not None,
        "timestamp": time.time(),
    }


@app.get("/public-key")
async def get_public_key():
    if PUBLIC_KEY is None:
        raise HTTPException(status_code=503, detail="oqs-python is required for key generation")
    return {"algorithm": SIG_ALG, "public_key_hex": PUBLIC_KEY.hex()}


@app.get("/compliance-status")
async def compliance_status():
    return {
        "certified": False,
        "attestation_ready": oqs is not None,
        "standards_alignment": ["ISO/IEC 42001", "ISO/IEC 23894"],
        "note": "Certification must come from an external accredited assessor; this service only emits evidence.",
    }


@app.on_event("startup")
async def startup_event():
    _log_attestation("service_started", "gateone_pqc_verifier")
    log.info("GATEONE PQC Verifier listening on %s:%s", VERIFIER_HOST, VERIFIER_PORT)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=VERIFIER_HOST, port=VERIFIER_PORT)
