"""Voice Assist Agent — accessibility-first voice command handler.

Designed for hands-free operation by users with mobility challenges.  The
agent:
- Listens for voice commands over a WebSocket connection from the gateway
- Converts commands to actions (navigate, describe, login, wizard steps)
- Synthesises speech responses via pyttsx3 (falls back to text only)
- Guides users through a hands-free setup wizard, login flow, and
  dashboard narration

WebSocket message protocol
--------------------------
Incoming (client → agent):

    {"command": "describe_dashboard" | "login" | "navigate" | "wizard_step",
     "payload": {...}}

Outgoing (agent → client):

    {"type": "voice_response", "text": str, "audio_b64": str | null}
"""

import asyncio
import base64
import io
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TTS helper
# ---------------------------------------------------------------------------

def _synth_to_bytes(text: str) -> Optional[bytes]:
    """Synthesise *text* to WAV bytes using pyttsx3, or return None."""
    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        buf = io.BytesIO()

        # pyttsx3 can save to file; write to temp path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as fh:
            data = fh.read()
        os.unlink(tmp_path)
        return data
    except Exception as exc:
        logger.debug("TTS synthesis failed: %s", exc)
        return None


def _tts_b64(text: str) -> Optional[str]:
    data = _synth_to_bytes(text)
    if data:
        return base64.b64encode(data).decode()
    return None


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

_WIZARD_STEPS = [
    "Welcome to Sovereignty AI Studio. Let's get you set up.",
    "Please say your username or type it in the box.",
    "Now say your password or use the password field.",
    "You're all set! Say 'go to dashboard' to continue.",
]


class VoiceAssistAgent:
    """Handles voice commands for accessibility, under Judge supervision."""

    AGENT_ID = "voice_assist"

    def __init__(self, judge: Any) -> None:
        self._judge = judge
        self._wizard_step: int = 0
        # Optional external send callback (set by gateway)
        self._send_callback: Optional[Callable] = None

    def set_send_callback(self, callback: Callable) -> None:
        """Register a coroutine to call when a response should be sent."""
        self._send_callback = callback

    async def handle_command(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a voice command message and return a response dict.

        Args:
            message: Dict with ``command`` and optional ``payload`` keys.

        Returns:
            Dict with ``type``, ``text``, and optional ``audio_b64``.
        """
        command = message.get("command", "")
        payload = message.get("payload", {})

        task = {"resource": "voice_assist", "command": command}
        approved, reason = await self._judge.approve_task(
            self.AGENT_ID, task
        )
        if not approved:
            return self._response(f"Voice assistant busy: {reason}")

        try:
            text = await self._dispatch(command, payload)
        except Exception as exc:
            logger.error("VoiceAssist error: %s", exc, exc_info=True)
            text = "I encountered an error. Please try again."
        finally:
            await self._judge.release_task(self.AGENT_ID, "voice_assist")

        response = self._response(text)
        if self._send_callback:
            asyncio.create_task(self._send_callback(response))
        return response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _response(text: str) -> Dict[str, Any]:
        return {
            "type": "voice_response",
            "text": text,
            "audio_b64": _tts_b64(text),
        }

    async def _dispatch(self, command: str, payload: Dict[str, Any]) -> str:
        handlers: Dict[str, Callable] = {
            "describe_dashboard": self._describe_dashboard,
            "login": self._login,
            "navigate": self._navigate,
            "wizard_step": self._wizard_step_handler,
            "help": self._help,
        }
        handler = handlers.get(command, self._unknown_command)
        return await handler(payload)

    async def _describe_dashboard(self, payload: Dict[str, Any]) -> str:
        return (
            "You are on the Sovereignty AI Studio dashboard. "
            "Available sections: Organizations, Projects, Agents, "
            "Analytics, Settings. Say a section name to navigate there."
        )

    async def _login(self, payload: Dict[str, Any]) -> str:
        username = payload.get("username", "")
        if username:
            return f"Logging in as {username}. Please confirm your password."
        return "Please say or enter your username to log in."

    async def _navigate(self, payload: Dict[str, Any]) -> str:
        target = payload.get("target", "")
        section_map = {
            "organizations": "organizations",
            "orgs": "organizations",
            "projects": "projects",
            "agents": "agents",
            "analytics": "analytics",
            "settings": "settings",
            "dashboard": "dashboard",
        }
        dest = section_map.get(target.lower(), "")
        if dest:
            return f"Navigating to {dest}."
        return f"I don't recognise '{target}'. Try: organizations, projects, agents, analytics, or settings."

    async def _wizard_step_handler(self, payload: Dict[str, Any]) -> str:
        step = self._wizard_step
        if step >= len(_WIZARD_STEPS):
            return "Setup complete. Welcome to Sovereignty AI Studio!"
        text = _WIZARD_STEPS[step]
        self._wizard_step = min(step + 1, len(_WIZARD_STEPS))
        return text

    async def _help(self, payload: Dict[str, Any]) -> str:
        return (
            "Available voice commands: describe dashboard, login, "
            "navigate, wizard step, help."
        )

    async def _unknown_command(self, payload: Dict[str, Any]) -> str:
        return (
            "I didn't understand that command. Say 'help' for a list "
            "of available commands."
        )
