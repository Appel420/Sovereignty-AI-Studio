"""Focused API tests for offline voice processing and Merkle provenance."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.v1.endpoints import provenance, voice
from app.services.local_stt_service import local_stt_service
from app.services.voice_interaction_service import voice_interaction_service


@pytest.fixture
def client():
    for session in voice_interaction_service.list_sessions():
        voice_interaction_service.end_session(session["session_id"])

    app = FastAPI()
    app.include_router(voice.router, prefix="/api/v1/voice")
    app.include_router(provenance.router, prefix="/api/v1/provenance")

    with TestClient(app) as test_client:
        yield test_client

    for session in voice_interaction_service.list_sessions():
        voice_interaction_service.end_session(session["session_id"])


def test_voice_process_creates_offline_session_without_exposing_device_fingerprint(client):
    fingerprint = "raw-device-fingerprint-123"

    response = client.post(
        "/api/v1/voice/process",
        json={"text": "hello", "device_fingerprint": fingerprint},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["offline"] is True
    assert payload["response_text"] == "[Offline mode] Received: 'hello'"
    assert fingerprint not in response.text

    session = voice_interaction_service.get_session(payload["session_id"])
    assert session is not None
    assert session.user_id != fingerprint
    assert fingerprint not in session.user_id


def test_voice_process_reuses_existing_session(client):
    first = client.post("/api/v1/voice/process", json={"text": "first turn"})
    second = client.post(
        "/api/v1/voice/process",
        json={
            "text": "second turn",
            "session_id": first.json()["session_id"],
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["session_id"] == first.json()["session_id"]
    assert second.json()["message_count"] == 4


def test_voice_input_returns_local_unavailable_status_without_creating_session(client):
    fingerprint = "input-device-fingerprint"
    original_model_path = local_stt_service.model_path
    initial_sessions = voice_interaction_service.list_sessions()
    local_stt_service.model_path = ""

    try:
        response = client.post(
            "/api/v1/voice/input",
            data={"device_fingerprint": fingerprint},
            files={"audio": ("clip.webm", b"placeholder-audio", "audio/webm")},
        )
    finally:
        local_stt_service.model_path = original_model_path

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert "processing" not in payload
    assert fingerprint not in response.text
    assert voice_interaction_service.list_sessions() == initial_sessions


def test_provenance_generate_and_verify_merkle_sha256_proof(client):
    generate = client.post(
        "/api/v1/provenance/proof/generate",
        json={
            "leaves": [
                {"message": "alpha", "sequence": 1},
                {"sequence": 2, "message": "beta"},
            ],
            "leaf_index": 1,
        },
    )

    assert generate.status_code == 200
    proof = generate.json()
    assert proof["proof_type"] == "merkle"
    assert proof["algorithm"] == "sha256"
    assert len(proof["merkle_root"]) == 64
    assert "ml-dsa" not in generate.text.lower()

    verify = client.post(
        "/api/v1/provenance/proof/verify",
        json={
            "leaf": {"message": "beta", "sequence": 2},
            "proof": proof,
        },
    )

    assert verify.status_code == 200
    assert verify.json()["valid"] is True


def test_provenance_verify_rejects_non_sha256_claims(client):
    proof = client.post(
        "/api/v1/provenance/proof/generate",
        json={"leaves": ["alpha", "beta"], "leaf_index": 1},
    ).json()
    proof["proof_type"] = "ml-dsa-87"
    proof["algorithm"] = "ml-dsa-87"

    verify = client.post(
        "/api/v1/provenance/proof/verify",
        json={"leaf": "beta", "proof": proof},
    )

    assert verify.status_code == 400
    assert "Merkle" in verify.json()["detail"]
