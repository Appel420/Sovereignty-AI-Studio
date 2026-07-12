"""Tests for durable, approval-gated voice coding collaboration."""

import tempfile

import pytest

from backend.app.services.local_stt_service import LocalSTTService
from backend.app.services.voice_collaboration_service import VoiceCollaborationService


class TestVoiceCollaborationService:
    def setup_method(self):
        self._directory = tempfile.TemporaryDirectory()
        self.service = VoiceCollaborationService(self._directory.name)
        self.task = self.service.create_task(
            goal="Add secure voice collaboration",
            acceptance_criteria=["Keep execution approval-gated"],
            agent_id="copilot",
            tests_required=["pytest tests/test_voice_collaboration.py"],
            allowed_paths=["backend/app/services/"],
        )

    def teardown_method(self):
        self._directory.cleanup()

    def test_task_is_durable(self):
        loaded = self.service.get_task(self.task["task_id"])
        assert loaded["goal"] == self.task["goal"]
        assert loaded["branch"] == "copilot"
        assert loaded["pending_approval"] is None

    def test_progress_rejects_out_of_scope_files(self):
        with pytest.raises(ValueError, match="approved task scope"):
            self.service.report_progress(
                self.task["task_id"], ["SGHv119.html"], [], "Review changes"
            )

    def test_execution_requires_matching_request(self):
        with pytest.raises(ValueError, match="No matching approval"):
            self.service.approve(self.task["task_id"], "execution")

        requested = self.service.request_approval(
            self.task["task_id"], "execution", "Run the approved checks"
        )
        assert requested["status"] == "awaiting_approval"
        approved = self.service.approve(self.task["task_id"], "execution")
        assert approved["status"] == "approved"
        assert approved["pending_approval"] is None

    @pytest.mark.asyncio
    async def test_default_collaboration_does_not_contact_remote_agent(self, monkeypatch):
        monkeypatch.delenv("VOICE_COLLAB_ALLOW_REMOTE_AGENT", raising=False)
        result = await self.service.collaborate(self.task["task_id"], "Please propose the change")
        assert result["execution_gated"] is True
        assert "Local task state was saved" in result["response"]


def test_stt_reports_missing_local_model():
    service = LocalSTTService(model_path="")
    result = service.transcribe_bytes(b"audio")
    assert result["status"] == "unavailable"
