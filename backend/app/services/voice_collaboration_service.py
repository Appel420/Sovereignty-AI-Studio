"""Durable, approval-gated coordination for voice-driven coding work."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_BRANCHES = {"grok": "ara-hardened", "claude": "claude", "gpt": "gpt", "copilot": "copilot"}
APPROVAL_ACTIONS = {"scope_change", "execution", "commit", "pull_request"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceCollaborationService:
    """Persist tasks locally and only produce proposals until user approval."""

    def __init__(self, storage_dir: str | None = None) -> None:
        root = storage_dir or os.getenv("VOICE_COLLAB_STATE_DIR", "data/voice-collaboration")
        self.storage_dir = Path(root)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        return self.storage_dir / f"{uuid.UUID(task_id)}.json"

    def _read(self, task_id: str) -> dict[str, Any] | None:
        path = self._path(task_id)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, task: dict[str, Any]) -> dict[str, Any]:
        task["updated_at"] = _now()
        target = self._path(task["task_id"])
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.storage_dir, delete=False
        ) as temporary:
            json.dump(task, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(target)
        return task

    def create_task(
        self,
        goal: str,
        acceptance_criteria: list[str],
        agent_id: str,
        tests_required: list[str] | None = None,
        allowed_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        if agent_id not in AGENT_BRANCHES:
            raise ValueError("Unknown coding agent")
        if not goal.strip() or not acceptance_criteria:
            raise ValueError("A goal and at least one acceptance criterion are required")
        task = {
            "task_id": str(uuid.uuid4()),
            "goal": goal.strip(),
            "acceptance_criteria": acceptance_criteria,
            "agent_id": agent_id,
            "branch": AGENT_BRANCHES[agent_id],
            "allowed_paths": allowed_paths or [],
            "tests_required": tests_required or [],
            "status": "planning",
            "next_step": "Agent must produce a scoped proposal.",
            "transcript": [],
            "decisions": [],
            "progress_reports": [],
            "files_changed": [],
            "validation": [],
            "commit_ids": [],
            "pending_approval": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        return self._write(task)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._read(task_id)

    def record_transcript(self, task_id: str, text: str) -> dict[str, Any]:
        task = self._require(task_id)
        task["transcript"].append({"at": _now(), "role": "user", "text": text})
        return self._write(task)

    def report_progress(
        self,
        task_id: str,
        files_changed: list[str],
        validation: list[dict[str, str]],
        next_step: str,
    ) -> dict[str, Any]:
        task = self._require(task_id)
        normalized_scopes = [s if s.endswith('/') else s + '/' for s in task["allowed_paths"]]
        if task["allowed_paths"] and any(
            not any(path.startswith(scope) for scope in normalized_scopes)
            for path in files_changed
        ):
            raise ValueError("Changed files exceed the approved task scope")
        task["files_changed"] = sorted(set(task["files_changed"] + files_changed))
        task["validation"] = validation
        task["next_step"] = next_step
        task["progress_reports"].append(
            {"at": _now(), "files_changed": files_changed, "validation": validation, "next_step": next_step}
        )
        return self._write(task)

    def request_approval(self, task_id: str, action: str, details: str) -> dict[str, Any]:
        if action not in APPROVAL_ACTIONS:
            raise ValueError("Unsupported approval action")
        task = self._require(task_id)
        task["pending_approval"] = {"action": action, "details": details, "requested_at": _now()}
        task["status"] = "awaiting_approval"
        task["next_step"] = f"Await explicit approval for {action}."
        return self._write(task)

    def approve(self, task_id: str, action: str) -> dict[str, Any]:
        task = self._require(task_id)
        pending = task.get("pending_approval")
        if not pending or pending["action"] != action:
            raise ValueError("No matching approval request exists")
        task["decisions"].append({"at": _now(), "action": action, "approved": True})
        task["pending_approval"] = None
        task["status"] = "approved"
        task["next_step"] = "Agent may proceed only with the approved action."
        return self._write(task)

    async def collaborate(self, task_id: str, transcript: str) -> dict[str, Any]:
        task = self.record_transcript(task_id, transcript)
        if task["pending_approval"]:
            return self._response(task, "Approval is pending; no coding action will be taken.")
        if os.getenv("VOICE_COLLAB_ALLOW_REMOTE_AGENT") != "1":
            return self._response(
                task,
                "Local task state was saved. Configure a local coding agent, or explicitly enable a permitted remote agent to receive a proposal.",
            )
        from app.services.ai_router import ai_router

        prompt = (
            f"Task goal: {task['goal']}\nAcceptance criteria: {task['acceptance_criteria']}\n"
            f"Approved branch: {task['branch']}\nAllowed paths: {task['allowed_paths']}\n"
            f"User transcript: {transcript}\n"
            "Respond with a concise scoped proposal only. Do not claim edits, run commands, commit, "
            "or change scope. Any edit must later include changed files, validation results, and next step."
        )
        response = await ai_router.chat(
            prompt=prompt,
            system="You are a coding-task coordinator. Stay within the approved task scope.",
            preferred_provider={"grok": "xai", "claude": "anthropic", "gpt": "openai"}.get(task["agent_id"]),
            max_tokens=512,
            temperature=0.1,
        )
        task["transcript"].append({"at": _now(), "role": "assistant", "text": response["text"]})
        task["next_step"] = "Review the proposal, then explicitly approve an execution request."
        task = self._write(task)
        return self._response(task, response["text"])

    @staticmethod
    def _response(task: dict[str, Any], response: str) -> dict[str, Any]:
        return {
            "status": task["status"],
            "response": response,
            "task": task,
            "execution_gated": True,
        }

    def _require(self, task_id: str) -> dict[str, Any]:
        task = self._read(task_id)
        if not task:
            raise ValueError("Voice collaboration task not found")
        return task


voice_collaboration_service = VoiceCollaborationService()
