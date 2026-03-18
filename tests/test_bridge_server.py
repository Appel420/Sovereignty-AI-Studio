import json

import pytest

import bridge


class DummyWS:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.remote_address = ("127.0.0.1", 12345)

    async def send(self, payload: str):
        self.sent.append(json.loads(payload))

    async def close(self):
        self.closed = True


class DummyServer:
    def __init__(self):
        self.closed = False
        self.waited = False

    def close(self):
        self.closed = True

    async def wait_closed(self):
        self.waited = True


@pytest.mark.asyncio
async def test_broadcast_ai_response_excludes_origin():
    srv = bridge.BridgeServer()
    sender = DummyWS()
    other = DummyWS()
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
    ws = DummyWS()

    async def fake_sovereign(msg: str, sys_prompt: str, agent: str = "sovereign") -> str:
        return "sovereign-response"

    monkeypatch.setattr(srv, "_chat_sovereign", fake_sovereign)

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
    ws = DummyWS()

    async def fake_sovereign(msg: str, sys_prompt: str, agent: str = "sovereign") -> str:
        assert msg == "route this"
        assert "sovereign" in sys_prompt.lower()
        return "from-sovereign"

    monkeypatch.setattr(srv, "_chat_sovereign", fake_sovereign)

    await srv.ai_chat(ws, msg="route this", agent="any-agent", context="ctx")

    assert ws.sent[0]["text"] == "from-sovereign"


@pytest.mark.asyncio
async def test_stop_closes_clients_and_server():
    srv = bridge.BridgeServer()
    ws1 = DummyWS()
    ws2 = DummyWS()
    srv.clients = {ws1, ws2}
    srv._server = DummyServer()

    await srv.stop()

    assert srv._stopping is True
    assert ws1.closed is True
    assert ws2.closed is True
    assert srv.clients == set()
    assert srv._server.closed is True
    assert srv._server.waited is True
