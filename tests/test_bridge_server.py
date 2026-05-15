"""Tests for the hardened FastAPI bridge server."""

import pytest
from fastapi.testclient import TestClient

import bridge


class DummyWebSocket:
    def __init__(self, headers=None, query_params=None):
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.accepted = False
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.sent.append(payload)


def test_smart_python_fix_sorts_generated_imports():
    code = "print(asyncio)\nprint(json)\nprint(os)"

    fixed = bridge.smart_python_fix(code, "NameError")

    assert fixed.splitlines()[:3] == ["import asyncio", "import json", "import os"]


def test_get_or_create_api_key_falls_back_to_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "API_KEY_FILE", tmp_path / "bridge_api_key")
    monkeypatch.setattr(bridge, "get_api_key_from_keychain", lambda: None)
    monkeypatch.setattr(bridge, "store_api_key_in_keychain", lambda _key: False)
    monkeypatch.delenv("SOVEREIGN_API_KEY", raising=False)

    key, source, persisted = bridge.get_or_create_api_key()
    cached_key, cached_source, cached_persisted = bridge.get_or_create_api_key()

    assert source == "file"
    assert persisted is True
    assert cached_key == key
    assert cached_source == "file"
    assert cached_persisted is True


def test_health_reports_runtime_key_source(monkeypatch):
    monkeypatch.setattr(bridge, "API_KEY_SOURCE", "environment")
    monkeypatch.setattr(bridge, "API_KEY_PERSISTED", False)
    client = TestClient(bridge.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["key_source"] == "environment"
    assert response.json()["key_persisted"] is False


def test_terminal_requires_x_sovereign_key(monkeypatch):
    async def fake_broadcast(_message):
        return None

    monkeypatch.setattr(bridge, "SOVEREIGN_API_KEY", "secret")
    monkeypatch.setattr(bridge, "sign_with_secure_enclave", lambda _data: "signature")
    monkeypatch.setattr(bridge.manager, "broadcast", fake_broadcast)
    client = TestClient(bridge.app)

    unauthorized = client.post("/terminal", json={"command": "echo hi"})
    authorized = client.post(
        "/terminal",
        json={"command": "echo hi"},
        headers={"X-Sovereign-Key": "secret"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["secure_enclave_signature"] == "signature"


@pytest.mark.asyncio
async def test_connection_manager_skips_sensitive_broadcasts_for_unauthenticated_clients(monkeypatch):
    monkeypatch.setattr(bridge, "SOVEREIGN_API_KEY", "secret")
    manager = bridge.ConnectionManager()
    anonymous = DummyWebSocket()
    authenticated = DummyWebSocket(query_params={"key": "secret"})

    anonymous_auth = await manager.connect(anonymous)
    authenticated_auth = await manager.connect(authenticated)
    await manager.broadcast({"type": "terminal_output", "message": "sensitive"})

    assert anonymous_auth is False
    assert authenticated_auth is True
    assert anonymous.sent == [{
        "type": "auth_status",
        "authenticated": False,
        "message": "Connected without a valid sovereign key; sensitive broadcasts are disabled.",
    }]
    assert authenticated.sent == [{"type": "terminal_output", "message": "sensitive"}]


def test_websocket_root_path_is_available(monkeypatch):
    monkeypatch.setattr(bridge, "SOVEREIGN_API_KEY", "secret")
    client = TestClient(bridge.app)

    with client.websocket_connect("/?key=secret") as websocket:
        websocket.close()
