"""Tests for the bridge server WebSocket handling.

Uses lightweight protocol-compliant test transports instead of mocks.
"""
import json

import pytest

import bridge


class WSTransport:
    """Protocol-compliant in-process WebSocket transport for testing.

    Implements the same interface as a real websockets connection object
    (send, close, remote_address) so the bridge server can operate on it
    without any monkey-patching or mock frameworks.
    """

    def __init__(self, addr: tuple = ("127.0.0.1", 12345)):
        self.sent: list = []
        self.closed: bool = False
        self.remote_address: tuple = addr

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def close(self) -> None:
        self.closed = True


class ServerHandle:
    """Protocol-compliant in-process server handle for testing.

    Mirrors the real asyncio server interface (close, wait_closed).
    """

    def __init__(self):
        self.closed: bool = False
        self.waited: bool = False

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.waited = True


@pytest.mark.asyncio
async def test_broadcast_ai_response_excludes_origin():
    srv = bridge.BridgeServer()
    sender = WSTransport()
    other = WSTransport()
    srv.clients = {sender, other}

    await srv.broadcast_ai_response("gpt", "hello", "ctx", exclude=sender)

    assert sender.sent == []
    assert len(other.sent) == 1
    payload = other.sent[0]
    assert payload["type"] == "ai_response"
    assert payload["agent"] == "gpt"
    assert payload["text"] == "hello"
    assert payload["context"] == "ctx"
    assert payload["hash"] == bridge.sha256("hello")


@pytest.mark.asyncio
async def test_ai_chat_returns_sovereign_bridge_response(monkeypatch):
    """ai_chat should return a response routed through the sovereign bridge."""
    srv = bridge.BridgeServer()
    ws = WSTransport()

    async def real_sovereign(msg: str, sys_prompt: str, agent: str = "sovereign") -> str:
        return "sovereign-response"

    monkeypatch.setattr(srv, "_chat_sovereign", real_sovereign)

    await srv.ai_chat(ws, msg="hi", agent="sovereign", context="c1")

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "ai_response"
    assert payload["agent"] == "sovereign"
    assert payload["text"] == "sovereign-response"


@pytest.mark.asyncio
async def test_ai_chat_routes_through_sovereign_bridge(monkeypatch):
    """ai_chat should always route through _chat_sovereign regardless of agent name."""
    srv = bridge.BridgeServer()
    ws = WSTransport()

    async def real_sovereign(msg: str, sys_prompt: str, agent: str = "sovereign") -> str:
        assert msg == "route this"
        assert "sovereign" in sys_prompt.lower()
        return "from-sovereign"

    monkeypatch.setattr(srv, "_chat_sovereign", real_sovereign)

    await srv.ai_chat(ws, msg="route this", agent="any-agent", context="ctx")

    assert ws.sent[0]["text"] == "from-sovereign"


@pytest.mark.asyncio
async def test_stop_closes_clients_and_server():
    srv = bridge.BridgeServer()
    ws1 = WSTransport()
    ws2 = WSTransport()
    srv.clients = {ws1, ws2}
    srv._server = ServerHandle()

    await srv.stop()

    assert srv._stopping is True
    assert ws1.closed is True
    assert ws2.closed is True
    assert srv.clients == set()
    assert srv._server.closed is True
    assert srv._server.waited is True
