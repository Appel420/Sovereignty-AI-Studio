import base64
import hashlib
import hmac
import json

import pytest

from backend.coordination.session_authorization import (
    SessionAuthorizationError,
    verify_session_proof,
)


SECRET = b"test-only-session-authority"


def make_proof(**overrides):
    payload = {
        "session_id": "session-001",
        "identity_id": "builder-001",
        "capabilities": ["ai.inference"],
        "branch": "copilot/main",
        "mode": "offline",
        "expires_at": 2_000_000_000,
    }
    payload.update(overrides)
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).rstrip(b"=")
    signature = hmac.new(SECRET, encoded, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{encoded.decode()}.{encoded_signature.decode()}"


def test_valid_session_proof_is_authorized():
    auth = verify_session_proof(make_proof(), secret=SECRET, now=1_000_000_000)
    assert auth.session_id == "session-001"
    assert auth.identity_id == "builder-001"
    assert auth.allows("ai.inference")
    assert auth.mode == "offline"


def test_tampered_proof_is_denied():
    proof = make_proof()
    payload, signature = proof.split(".", 1)
    tampered = payload[:-1] + ("A" if payload[-1] != "A" else "B")
    with pytest.raises(SessionAuthorizationError, match="invalid session proof signature"):
        verify_session_proof(f"{tampered}.{signature}", secret=SECRET, now=1_000_000_000)


def test_expired_proof_is_denied():
    with pytest.raises(SessionAuthorizationError, match="expired"):
        verify_session_proof(make_proof(expires_at=10), secret=SECRET, now=11)


def test_missing_inference_capability_is_denied():
    auth = verify_session_proof(
        make_proof(capabilities=["memory.read"]), secret=SECRET, now=1_000_000_000
    )
    assert not auth.allows("ai.inference")


def test_session_identity_cannot_be_replaced_by_caller_label():
    auth = verify_session_proof(make_proof(), secret=SECRET, now=1_000_000_000)
    assert auth.identity_id == "builder-001"
    assert auth.session_id != auth.identity_id
