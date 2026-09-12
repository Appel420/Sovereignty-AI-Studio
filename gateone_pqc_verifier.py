#!/usr/bin/env python3
"""GATEONE PQC verifier — fail-closed attestation service."""
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
    import oqs
except ImportError:
    oqs = None

try:
    from core.security.tpm_attestation import TPMAttester
except ImportError:
    TPMAttester = None  # type: ignore[assignment]

try:
    from sovereign_vault import SovereignVault
except ImportError:
    class SovereignVault:
        def log_event(self, event: str, data: dict[str, Any]) -> None:
            logging.getLogger("gateone").info("%s %s", event, data)

try:
    from scar_log import ScarLog
except ImportError:
    class ScarLog:
        def __init__(self, path: Path): self.path = path
        def append(self, entry: dict[str, Any]) -> None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")

log = logging.getLogger("gateone")
RUNTIME = ConfigFixer(defaults={
    "GATEONE_VERIFIER_PORT": 9899,
    "GATEONE_VERIFIER_HOST": "127.0.0.1",
    "GATEONE_KEY_DIR": "/etc/gateone/keys",
    "GATEONE_SCAR_LOG_PATH": "/var/log/gateone_pqc_scar.log",
}).fix_env_config()
SIG_ALG = "ML-DSA-87"
VERIFIER_HOST = str(RUNTIME["GATEONE_VERIFIER_HOST"])
VERIFIER_PORT = int(RUNTIME["GATEONE_VERIFIER_PORT"])
KEY_DIR = Path(str(RUNTIME["GATEONE_KEY_DIR"]))
SCAR_LOG_PATH = Path(str(RUNTIME["GATEONE_SCAR_LOG_PATH"]))
KEY_DIR.mkdir(parents=True, exist_ok=True)
VAULT = SovereignVault()
SCAR = ScarLog(SCAR_LOG_PATH)
app = FastAPI(title="GATEONE PQC Verifier", version="1.2.0")

class AttestationToken(BaseModel):
    attestation_token: str
    max_age_seconds: int = Field(300, ge=60, le=3600)

class AttestationResponse(BaseModel):
    valid: bool
    node_id: Optional[str] = None
    algorithm: Optional[str] = None
    dilithium_valid: Optional[bool] = None
    tpm_valid: Optional[bool] = None
    runtime_identity: Optional[str] = None
    measurement_digest: Optional[str] = None
    reason: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)

def _log_attestation(event: str, node_id: Optional[str], extra: dict[str, Any] | None = None) -> None:
    entry: dict[str, Any] = {"ts": int(time.time()), "event": event, "node_id": node_id, "service": "gateone_pqc_verifier"}
    if extra: entry.update(extra)
    SCAR.append(entry)
    VAULT.log_event("pqc_attestation", entry)

def _load_signer():
    if oqs is None: return None, None, None
    signer = oqs.Signature(SIG_ALG)
    pub_path, priv_path = KEY_DIR / f"{SIG_ALG}.pub", KEY_DIR / f"{SIG_ALG}.priv"
    if priv_path.exists() and pub_path.exists():
        private_key, public_key = priv_path.read_bytes(), pub_path.read_bytes()
        signer.import_secret_key(private_key)
        return signer, public_key, private_key
    public_key = signer.generate_keypair(); private_key = signer.export_secret_key()
    priv_path.write_bytes(private_key); pub_path.write_bytes(public_key); priv_path.chmod(0o600)
    return signer, public_key, private_key

SIGNER, PUBLIC_KEY, PRIVATE_KEY = _load_signer()

def _tpm_verify(quote: dict[str, Any] | None, *, runtime_identity: str, measurement_digest: str, nonce: bytes) -> tuple[bool, dict[str, Any]]:
    if not quote or TPMAttester is None:
        return False, {"status": "attestation_provider_unavailable"}
    try:
        result = TPMAttester().attest(
            public_key=quote.get("public_key"), message=quote.get("message"), signature=quote.get("signature"),
            nonce=nonce, runtime_identity=runtime_identity, measurement_digest=measurement_digest,
        )
        return bool(result.verified), result.details
    except Exception as exc:
        log.warning("TPM attestation failed: %s", exc)
        return False, {"status": "verification_error", "error": str(exc)}

@app.post("/verify-attestation", response_model=AttestationResponse)
async def verify_attestation(token: AttestationToken):
    try:
        if SIGNER is None or PUBLIC_KEY is None:
            raise HTTPException(status_code=503, detail="oqs-python is required for ML-DSA verification")
        data = json.loads(token.attestation_token)
        payload = data.get("payload", {})
        signature = bytes.fromhex(data.get("signature", ""))
        public_key = bytes.fromhex(data.get("public_key", ""))
        quote = data.get("tpm_quote")
        node_id = str(payload.get("node_id", "unknown"))
        runtime_identity = str(payload.get("runtime_identity", ""))
        measurement_digest = str(payload.get("measurement_digest", ""))
        nonce_hex = str(payload.get("nonce", ""))
        nonce = bytes.fromhex(nonce_hex) if nonce_hex else b""
        age = time.time() - float(payload.get("timestamp", 0))
        if age < 0 or age > token.max_age_seconds:
            _log_attestation("attestation_failed", node_id, {"reason": "token_too_old_or_future", "age": age})
            return AttestationResponse(valid=False, reason="token_too_old_or_future", node_id=node_id)
        if not runtime_identity or not measurement_digest or not nonce:
            _log_attestation("attestation_failed", node_id, {"reason": "missing_runtime_binding"})
            return AttestationResponse(valid=False, node_id=node_id, reason="missing_runtime_binding")
        message_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        is_dilithium_valid = SIGNER.verify(message_bytes, signature, public_key)
        is_tpm_valid, tpm_details = _tpm_verify(quote, runtime_identity=runtime_identity, measurement_digest=measurement_digest, nonce=nonce)
        valid = bool(is_dilithium_valid and is_tpm_valid)
        _log_attestation("attestation_success" if valid else "attestation_failed", node_id, {
            "algorithm": SIG_ALG, "dilithium_valid": is_dilithium_valid, "tpm_valid": is_tpm_valid,
            "runtime_identity": runtime_identity, "measurement_digest": measurement_digest,
            "nonce_sha256": __import__("hashlib").sha256(nonce).hexdigest(), "tpm_details": tpm_details,
        })
        return AttestationResponse(valid=valid, node_id=node_id, algorithm=SIG_ALG,
            dilithium_valid=is_dilithium_valid, tpm_valid=is_tpm_valid,
            runtime_identity=runtime_identity, measurement_digest=measurement_digest,
            reason=None if valid else "pqc_or_tpm_verification_failed")
    except HTTPException: raise
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        _log_attestation("attestation_error", None, {"error": str(exc)})
        return AttestationResponse(valid=False, reason="malformed_attestation")
    except Exception as exc:
        _log_attestation("attestation_error", None, {"error": str(exc)})
        return AttestationResponse(valid=False, reason="attestation_verification_error")

@app.get("/health")
async def health():
    return {"status":"healthy","service":"GATEONE PQC Verifier","algorithm":SIG_ALG,"port":VERIFIER_PORT,"host":VERIFIER_HOST,"keys_persisted":PRIVATE_KEY is not None and PUBLIC_KEY is not None,"oqs_available":oqs is not None,"tpm_provider":TPMAttester is not None,"timestamp":time.time()}

@app.get("/public-key")
async def get_public_key():
    if PUBLIC_KEY is None: raise HTTPException(status_code=503, detail="oqs-python is required for key generation")
    return {"algorithm":SIG_ALG,"public_key_hex":PUBLIC_KEY.hex()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=VERIFIER_HOST, port=VERIFIER_PORT)
