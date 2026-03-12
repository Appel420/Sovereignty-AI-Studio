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
async def test_ai_chat_returns_offline_message_without_keys():
    srv = bridge.BridgeServer()
    ws = DummyWS()

    await srv.ai_chat(ws, msg="hi", agent="gpt", context="c1")

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "ai_response"
    assert payload["agent"] == "gpt"
    assert "offline" in payload["text"]
    assert "OPENAI_API_KEY" in payload["text"]


@pytest.mark.asyncio
async def test_ai_chat_routes_to_private_gpt_handler(monkeypatch):
    srv = bridge.BridgeServer()
    ws = DummyWS()

    async def fake_chat_gpt(msg: str, sys_prompt: str) -> str:
        assert msg == "route this"
        assert "SuperGrok" in sys_prompt
        return "from-gpt"

    monkeypatch.setattr(bridge, "OPENAI_OK", True)
    monkeypatch.setattr(bridge, "OPENAI_KEY", "test-key")
    monkeypatch.setattr(srv, "_chat_gpt", fake_chat_gpt)

    await srv.ai_chat(ws, msg="route this", agent="gpt", context="ctx")

    assert ws.sent[0]["text"] == "from-gpt"


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
