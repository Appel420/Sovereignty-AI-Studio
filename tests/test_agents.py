"""Tests for the multi-agent system components.

Covers:
- JudgeAgent resource locking and approval logic
- AIRouterAgent provider selection
- PluginAgent plugin discovery and execution
- VoiceAssistAgent command dispatch
- EventBus send/process lifecycle
"""

import asyncio
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── JudgeAgent ────────────────────────────────────────────────────────────────

from agents.judge_agent.judge import JudgeAgent


class TestJudgeAgent:
    def setup_method(self):
        self.judge = JudgeAgent()

    @pytest.mark.asyncio
    async def test_approve_new_resource(self):
        approved, reason = await self.judge.approve_task(
            "agent_a", {"resource": "openai"}
        )
        assert approved is True
        assert "granted" in reason

    @pytest.mark.asyncio
    async def test_reject_locked_resource(self):
        await self.judge.approve_task("agent_a", {"resource": "openai"})
        approved, reason = await self.judge.approve_task(
            "agent_b", {"resource": "openai"}
        )
        assert approved is False
        assert "locked" in reason

    @pytest.mark.asyncio
    async def test_same_agent_reacquire(self):
        await self.judge.approve_task("agent_a", {"resource": "openai"})
        approved, _ = await self.judge.approve_task(
            "agent_a", {"resource": "openai"}
        )
        assert approved is True

    @pytest.mark.asyncio
    async def test_release_unlocks_resource(self):
        await self.judge.approve_task("agent_a", {"resource": "openai"})
        await self.judge.release_task("agent_a", "openai")
        approved, _ = await self.judge.approve_task(
            "agent_b", {"resource": "openai"}
        )
        assert approved is True

    @pytest.mark.asyncio
    async def test_task_log_records_events(self):
        await self.judge.approve_task("agent_a", {"resource": "r1"})
        log = self.judge.get_task_log()
        assert len(log) == 1
        assert log[0]["agent_id"] == "agent_a"
        assert log[0]["approved"] is True

    @pytest.mark.asyncio
    async def test_release_without_hold_is_safe(self):
        # Should not raise
        await self.judge.release_task("agent_x", "nonexistent_resource")


# ── AIRouterAgent provider selection ─────────────────────────────────────────

from agents.ai_router_agent.router import (
    _select_provider,
    _key_available,
    PROVIDER_OPENAI,
    PROVIDER_ANTHROPIC,
    PROVIDER_XAI,
)


class TestAIRouterProviderSelection:
    def test_no_keys_returns_none(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        result = _select_provider("code")
        assert result is None

    def test_selects_openai_for_code(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        result = _select_provider("code")
        assert result == PROVIDER_OPENAI

    def test_falls_back_when_preferred_missing(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        # "code" prefers openai, but falls back to anthropic
        result = _select_provider("code")
        assert result == PROVIDER_ANTHROPIC

    def test_key_available_true(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "abc")
        assert _key_available(PROVIDER_XAI) is True

    def test_key_available_false(self, monkeypatch):
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        assert _key_available(PROVIDER_XAI) is False


# ── PluginAgent ───────────────────────────────────────────────────────────────

import tempfile
from pathlib import Path
from agents.plugin_agent.plugin_manager import PluginAgent


class TestPluginAgent:
    def setup_method(self):
        self.judge = JudgeAgent()
        self.agent = PluginAgent(self.judge)

    def _make_plugin_dir(self, tmp_path: Path) -> Path:
        """Create a minimal valid plugin in *tmp_path*."""
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        manifest = {
            "id": "my_plugin",
            "name": "My Plugin",
            "version": "1.0.0",
            "entry": "main.py",
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
        (plugin_dir / "main.py").write_text(
            "def run(task):\n    return {'ok': True}\n"
        )
        return plugin_dir

    def test_discover_finds_plugin(self, tmp_path, monkeypatch):
        import agents.plugin_agent.plugin_manager as pm
        self._make_plugin_dir(tmp_path)
        monkeypatch.setattr(pm, "_PLUGIN_SDK_DIR", tmp_path)
        ids = self.agent.discover()
        assert "my_plugin" in ids

    def test_discover_empty_dir(self, tmp_path, monkeypatch):
        import agents.plugin_agent.plugin_manager as pm
        monkeypatch.setattr(pm, "_PLUGIN_SDK_DIR", tmp_path)
        ids = self.agent.discover()
        assert ids == []

    @pytest.mark.asyncio
    async def test_run_plugin_success(self, tmp_path, monkeypatch):
        import agents.plugin_agent.plugin_manager as pm
        self._make_plugin_dir(tmp_path)
        monkeypatch.setattr(pm, "_PLUGIN_SDK_DIR", tmp_path)
        self.agent.discover()
        success, result = await self.agent.run_plugin("my_plugin", {"x": 1})
        assert success is True
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_run_undiscovered_plugin(self):
        success, result = await self.agent.run_plugin("ghost_plugin", {})
        assert success is False
        assert "not discovered" in result


# ── VoiceAssistAgent ──────────────────────────────────────────────────────────

from agents.voice_assist_agent.voice_manager import VoiceAssistAgent


class TestVoiceAssistAgent:
    def setup_method(self):
        self.judge = JudgeAgent()
        self.agent = VoiceAssistAgent(self.judge)

    @pytest.mark.asyncio
    async def test_describe_dashboard(self):
        resp = await self.agent.handle_command(
            {"command": "describe_dashboard", "payload": {}}
        )
        assert resp["type"] == "voice_response"
        assert "dashboard" in resp["text"].lower()

    @pytest.mark.asyncio
    async def test_navigate_known_section(self):
        resp = await self.agent.handle_command(
            {"command": "navigate", "payload": {"target": "projects"}}
        )
        assert "projects" in resp["text"].lower()

    @pytest.mark.asyncio
    async def test_navigate_unknown_section(self):
        resp = await self.agent.handle_command(
            {"command": "navigate", "payload": {"target": "foobar"}}
        )
        assert "foobar" in resp["text"]

    @pytest.mark.asyncio
    async def test_wizard_steps_advance(self):
        responses = []
        for _ in range(4):
            resp = await self.agent.handle_command(
                {"command": "wizard_step", "payload": {}}
            )
            responses.append(resp["text"])
        # All responses should be strings
        for text in responses:
            assert isinstance(text, str) and len(text) > 0

    @pytest.mark.asyncio
    async def test_unknown_command(self):
        resp = await self.agent.handle_command(
            {"command": "fly_to_moon", "payload": {}}
        )
        assert resp["type"] == "voice_response"
        assert "help" in resp["text"].lower() or "understand" in resp["text"].lower()

    @pytest.mark.asyncio
    async def test_help_command(self):
        resp = await self.agent.handle_command({"command": "help", "payload": {}})
        assert "voice commands" in resp["text"].lower()


# ── EventBus ──────────────────────────────────────────────────────────────────

from event_bus import bus as event_bus


class TestEventBus:
    def setup_method(self):
        # Drain the in-process queue between tests
        from event_bus.bus import _local_queue
        while not _local_queue.empty():
            try:
                _local_queue.get_nowait()
            except Exception:
                break

    @pytest.mark.asyncio
    async def test_send_and_receive(self):
        received = []

        async def handler(task):
            received.append(task)

        event_bus.register_handler("test_agent", handler)
        await event_bus.send_event("test_agent", {"action": "ping"})

        # Verify the event lands in the local queue
        from event_bus.bus import _local_queue
        event = await asyncio.wait_for(_local_queue.get(), timeout=1.0)
        assert event["agent_id"] == "test_agent"
        assert event["task"]["action"] == "ping"

    @pytest.mark.asyncio
    async def test_send_populates_queue(self):
        from event_bus.bus import _local_queue
        await event_bus.send_event("any_agent", {"x": 1})
        assert not _local_queue.empty()
