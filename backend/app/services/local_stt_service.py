"""Offline speech-to-text backed by a locally provisioned Vosk model."""

import json
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any


class LocalSTTService:
    """Transcribe audio without network access or model downloads."""

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or os.getenv("VOSK_MODEL_PATH", "")

    def status(self) -> dict[str, Any]:
        return {
            "engine": "vosk",
            "offline": True,
            "model_configured": bool(self.model_path),
            "model_available": bool(self.model_path and Path(self.model_path).is_dir()),
            "ffmpeg_available": shutil.which("ffmpeg") is not None,
        }

    def transcribe_bytes(self, audio: bytes, suffix: str = ".webm") -> dict[str, Any]:
        """Convert browser audio to PCM WAV and transcribe it with local Vosk."""
        if not audio:
            return {"status": "error", "error": "Audio upload is empty"}
        if not self.model_path or not Path(self.model_path).is_dir():
            return {
                "status": "unavailable",
                "error": "Local STT model is not configured. Set VOSK_MODEL_PATH.",
            }
        if not shutil.which("ffmpeg"):
            return {
                "status": "unavailable",
                "error": "ffmpeg is required to decode microphone audio locally.",
            }

        try:
            from vosk import KaldiRecognizer, Model
        except ImportError:
            return {
                "status": "unavailable",
                "error": "Vosk is not installed. Install the local STT dependency.",
            }

        safe_suffix = "".join(character for character in suffix if character.isalnum())[:10] or "webm"
        with tempfile.TemporaryDirectory(prefix="sia-stt-") as directory:
            source = Path(directory) / f"audio.{safe_suffix}"
            wav_path = Path(directory) / "audio.wav"
            source.write_bytes(audio)
            conversion = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(source), "-ar", "16000", "-ac", "1",
                    "-f", "wav", str(wav_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if conversion.returncode != 0:
                return {"status": "error", "error": "Unable to decode microphone audio"}

            with wave.open(str(wav_path), "rb") as audio_file:
                if audio_file.getnchannels() != 1 or audio_file.getframerate() != 16000:
                    return {"status": "error", "error": "Invalid decoded audio format"}
                recognizer = KaldiRecognizer(Model(self.model_path), audio_file.getframerate())
                while chunk := audio_file.readframes(4000):
                    recognizer.AcceptWaveform(chunk)
                result = json.loads(recognizer.FinalResult())

        text = str(result.get("text", "")).strip()
        return {
            "status": "completed",
            "text": text,
            "engine": "vosk",
            "offline": True,
        }


local_stt_service = LocalSTTService()
