"""Local-only bridge from avatar interaction output to the existing Piper TTS service.

The avatar service remains text/personality-only. This module is the glue layer:
avatar text -> Piper. No network or provider fallback is introduced here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.services.piper_tts_service import piper_service
from app.services.voice_interaction_service import voice_interaction_service


@dataclass(frozen=True)
class AvatarSpeechResult:
    """Result of a fail-closed avatar speech request."""

    text: str
    voice_id: str
    audio_path: Optional[str]
    spoken: bool
    error: Optional[str] = None


def avatar_speech_input(interaction: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Extract text and voice identity from a successful avatar interaction.

    This function is deliberately side-effect free. The avatar service never
    acquires an audio or network dependency through this contract.
    """
    if interaction.get("error"):
        return None

    text = interaction.get("response")
    voice_id = interaction.get("voice_id")
    if not isinstance(text, str) or not text.strip():
        return None
    if not isinstance(voice_id, str) or not voice_id.strip():
        return None

    return {"text": text, "voice_id": voice_id}


def speak_avatar_response(
    text: str,
    voice_id: str,
    *,
    output_file: Optional[str] = None,
) -> AvatarSpeechResult:
    """Synthesize avatar text through the existing local Piper service only.

    ``voice_id`` is validated against the existing voice catalog. Actual model
    selection remains owned by PiperTTSService/PIPER_MODEL_PATH; this bridge
    does not invent a new model lookup or network path.
    """
    if not text.strip():
        return AvatarSpeechResult(text, voice_id, None, False, "empty text")

    valid_voice_ids = {
        voice["id"] for voice in voice_interaction_service.get_available_voices()
    }
    if voice_id not in valid_voice_ids:
        return AvatarSpeechResult(
            text, voice_id, None, False, "voice engine not configured: unknown voice_id"
        )

    audio_path = piper_service.text_to_speech(text, output_file=output_file)
    if not audio_path:
        return AvatarSpeechResult(
            text, voice_id, None, False, "voice engine not configured"
        )

    return AvatarSpeechResult(text, voice_id, audio_path, True)


def interact_and_speak(
    avatar_service: Any,
    avatar_id: str,
    message: str,
    *,
    output_file: Optional[str] = None,
) -> AvatarSpeechResult | Dict[str, Any]:
    """Glue contract: interact first, then optionally speak locally.

    The avatar interaction remains authoritative for text. Piper is invoked
    only after a successful interaction. No cloud fallback is permitted.
    """
    interaction = avatar_service.interact(avatar_id, message)
    speech_input = avatar_speech_input(interaction)
    if speech_input is None:
        return interaction

    avatar = avatar_service.get_avatar(avatar_id) or {}
    voice_id = avatar.get("voice_id", speech_input["voice_id"])
    return speak_avatar_response(
        speech_input["text"], voice_id, output_file=output_file
    )
