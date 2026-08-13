"""
Piper TTS Integration for Alert Audio Notifications
Provides text-to-speech capabilities for live alerts
"""
import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class PiperTTSService:
    """Service for converting alert text to speech using Piper."""

    def __init__(self, piper_dir: str | None = None, model_path: str | None = None):
        """
        Initialize Piper TTS service.

        Args:
            piper_dir: Path to piper installation directory.
            model_path: Path to piper voice model (.onnx file).
        """
        self.piper_dir = piper_dir or os.path.join(
            Path(__file__).parent.parent.parent.parent,
            "piper-tts",
        )
        self.model_path = model_path or os.getenv(
            "PIPER_MODEL_PATH", os.getenv("PIPER_MODEL", "")
        )
        self.piper_executable = self._find_piper_executable()

    def _find_piper_executable(self) -> str | None:
        """Find the piper executable."""
        possible_paths = [
            os.path.join(self.piper_dir, "piper"),
            os.path.join(self.piper_dir, "build", "piper"),
            "/usr/local/bin/piper",
            "/usr/bin/piper",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        try:
            result = subprocess.run(
                ["which", "piper"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            logger.debug("Unable to locate Piper in PATH: %s", exc)

        logger.warning("Piper executable not found. Audio alerts will be disabled.")
        return None

    def text_to_speech(self, text: str, output_file: str | None = None) -> str | None:
        """
        Convert text to speech.

        Args:
            text: Text to convert.
            output_file: Output file path (optional, creates temp file if not provided).

        Returns:
            Path to the generated audio file, or None if failed.
        """
        if not self.piper_executable:
            logger.warning("Piper not available, skipping TTS")
            return None

        if not self.model_path or not os.path.exists(self.model_path):
            logger.warning("Piper model not found, skipping TTS")
            return None

        if not output_file:
            fd, output_file = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

        try:
            cmd = [
                self.piper_executable,
                "--model",
                self.model_path,
                "--output_file",
                output_file,
            ]
            result = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0 and os.path.exists(output_file):
                logger.info("Generated TTS audio: %s", output_file)
                return output_file

            logger.error("Piper TTS failed: %s", result.stderr)
            return None
        except (OSError, subprocess.SubprocessError) as exc:
            logger.error("Error running Piper TTS: %s", exc)
            return None

    def speak_alert(
        self, alert_title: str, alert_message: str, severity: str = "medium"
    ) -> bool:
        """
        Speak an alert using TTS.

        Args:
            alert_title: Alert title.
            alert_message: Alert message.
            severity: Alert severity (low, medium, high, critical).

        Returns:
            True if successful, False otherwise.
        """
        if severity in ["high", "critical"]:
            spoken_text = f"Alert! {alert_title}. {alert_message}"
        else:
            spoken_text = f"{alert_title}. {alert_message}"

        audio_file = self.text_to_speech(spoken_text)
        if audio_file:
            return self._play_audio(audio_file)

        return False

    def _play_audio(self, audio_file: str) -> bool:
        """Play an audio file and remove the temporary file afterward."""
        try:
            players = [
                ["aplay", audio_file],
                ["afplay", audio_file],
                [
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{audio_file}').PlaySync()",
                ],
            ]

            for player_cmd in players:
                try:
                    result = subprocess.run(
                        player_cmd,
                        capture_output=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode == 0:
                        logger.info("Played audio file: %s", audio_file)
                        return True
                except FileNotFoundError:
                    continue
                except (OSError, subprocess.SubprocessError) as exc:
                    logger.warning(
                        "Failed to play with %s: %s", player_cmd[0], exc
                    )
                    continue

            logger.warning("No audio player found")
            return False
        except (OSError, subprocess.SubprocessError) as exc:
            logger.error("Error playing audio: %s", exc)
            return False
        finally:
            try:
                if os.path.exists(audio_file):
                    os.unlink(audio_file)
            except OSError as exc:
                logger.debug("Unable to remove temporary audio file: %s", exc)


piper_service = PiperTTSService()
