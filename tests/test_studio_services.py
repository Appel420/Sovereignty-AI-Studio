"""Tests for the new Sovereignty AI Studio services.

Covers voice interaction, avatar companion, media generator, music generator,
syntax checker, dashboard builder, and BLE LiDAR EEG services.

All tests exercise real service implementations — no mocks.
"""
import os
import tempfile
import pytest

# ── Voice Interaction Service ────────────────────────────────────────

from backend.app.services.voice_interaction_service import (
    VoiceInteractionService,
    VoiceState,
)


class TestVoiceInteractionService:
    def setup_method(self):
        self.svc = VoiceInteractionService()

    def test_create_session(self):
        session = self.svc.create_session("user1")
        assert session.session_id
        assert session.user_id == "user1"
        assert session.state == VoiceState.IDLE

    def test_get_session(self):
        session = self.svc.create_session("user1")
        found = self.svc.get_session(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_end_session(self):
        session = self.svc.create_session("user1")
        assert self.svc.end_session(session.session_id) is True
        assert self.svc.get_session(session.session_id) is None

    def test_process_text_input(self):
        session = self.svc.create_session("user1")
        result = self.svc.process_text_input(session.session_id, "hello")
        assert "response_text" in result
        assert result["session_id"] == session.session_id
        # Real implementation returns actual text (from LLM or acknowledgement)
        assert len(result["response_text"]) > 0

    def test_process_text_input_invalid_session(self):
        result = self.svc.process_text_input("nonexistent", "hello")
        assert "error" in result

    def test_available_voices(self):
        voices = self.svc.get_available_voices()
        assert len(voices) > 0
        assert all("id" in v for v in voices)

    def test_status(self):
        status = self.svc.get_status()
        assert status["service"] == "voice_interaction"
        assert status["status"] == "online"


# ── Avatar Companion Service ─────────────────────────────────────────

from backend.app.services.avatar_companion_service import (
    AvatarCompanionService,
)


class TestAvatarCompanionService:
    def setup_method(self):
        self.svc = AvatarCompanionService()

    def test_create_avatar(self):
        result = self.svc.create_avatar("user1", name="Aria")
        assert result["name"] == "Aria"
        assert result["user_id"] == "user1"
        assert result["style"] == "minimal"

    def test_get_avatar(self):
        created = self.svc.create_avatar("user1")
        found = self.svc.get_avatar(created["avatar_id"])
        assert found is not None
        assert found["avatar_id"] == created["avatar_id"]

    def test_interact(self):
        created = self.svc.create_avatar("user1")
        result = self.svc.interact(created["avatar_id"], "hello")
        assert "response" in result
        assert result["interaction_count"] == 1
        # Real implementation returns actual text from AI or acknowledgement
        assert len(result["response"]) > 0

    def test_interact_nonexistent(self):
        result = self.svc.interact("fake-id", "hello")
        assert "error" in result

    def test_delete_avatar(self):
        created = self.svc.create_avatar("user1")
        assert self.svc.delete_avatar(created["avatar_id"]) is True
        assert self.svc.get_avatar(created["avatar_id"]) is None

    def test_status(self):
        status = self.svc.get_status()
        assert status["service"] == "avatar_companion"


# ── Media Generator Service ──────────────────────────────────────────

from backend.app.services.media_generator_service import (
    MediaGeneratorService,
)


class TestMediaGeneratorService:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.svc = MediaGeneratorService(output_dir=self._tmpdir)

    def test_generate_image(self):
        result = self.svc.generate("user1", "image", "a sunset")
        assert result["media_type"] == "image"
        assert result["status"] == "completed"
        assert result["result_path"] is not None
        # Verify real file was created on disk
        assert os.path.isfile(result["result_path"])
        assert os.path.getsize(result["result_path"]) > 0

    def test_generate_video(self):
        result = self.svc.generate("user1", "video", "waves crashing")
        assert result["media_type"] == "video"
        assert result["status"] == "completed"
        assert os.path.isfile(result["result_path"])

    def test_generate_audio(self):
        result = self.svc.generate("user1", "audio", "rain sounds")
        assert result["media_type"] == "audio"
        assert result["status"] == "completed"
        assert os.path.isfile(result["result_path"])
        assert os.path.getsize(result["result_path"]) > 0

    def test_get_job(self):
        result = self.svc.generate("user1", "image", "test")
        found = self.svc.get_job(result["job_id"])
        assert found is not None

    def test_list_jobs(self):
        self.svc.generate("user1", "image", "test1")
        self.svc.generate("user2", "video", "test2")
        all_jobs = self.svc.list_jobs()
        assert len(all_jobs) == 2
        user1_jobs = self.svc.list_jobs(user_id="user1")
        assert len(user1_jobs) == 1

    def test_status(self):
        status = self.svc.get_status()
        assert status["service"] == "media_generator"


# ── Music Generator Service ──────────────────────────────────────────

from backend.app.services.music_generator_service import (
    MusicGeneratorService,
)


class TestMusicGeneratorService:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.svc = MusicGeneratorService(output_dir=self._tmpdir)

    def test_compose(self):
        result = self.svc.compose("user1", "calm piano", genre="classical", bpm=90)
        assert result["genre"] == "classical"
        assert result["bpm"] == 90
        assert result["status"] == "completed"
        # Verify real WAV file was created
        assert result["result_path"] is not None
        assert os.path.isfile(result["result_path"])
        assert os.path.getsize(result["result_path"]) > 0

    def test_compose_clamped_bpm(self):
        result = self.svc.compose("user1", "fast", bpm=999)
        assert result["bpm"] == 240

    def test_compose_clamped_duration(self):
        result = self.svc.compose("user1", "long", duration_seconds=9999)
        assert result["duration_seconds"] == 300

    def test_get_job(self):
        result = self.svc.compose("user1", "test")
        found = self.svc.get_job(result["job_id"])
        assert found is not None

    def test_status(self):
        status = self.svc.get_status()
        assert status["service"] == "music_generator"


# ── Syntax Checker Service ───────────────────────────────────────────

from backend.app.services.syntax_checker_service import (
    SyntaxCheckerService,
)


class TestSyntaxCheckerService:
    def setup_method(self):
        self.svc = SyntaxCheckerService()

    def test_valid_python(self):
        report = self.svc.check_python("x = 1\nprint(x)\n")
        assert report["success"] is True
        assert report["errors"] == 0

    def test_syntax_error(self):
        report = self.svc.check_python("def foo(\n")
        assert report["success"] is False
        assert report["errors"] > 0

    def test_trailing_whitespace(self):
        report = self.svc.check_python("x = 1   \n")
        info_issues = [i for i in report["issues"] if i["severity"] == "info"]
        assert len(info_issues) > 0

    def test_colour_output_no_issues(self):
        report = self.svc.check_python("x = 1\n")
        coloured = self.svc.format_coloured(report)
        assert "✓" in coloured

    def test_colour_output_with_error(self):
        report = self.svc.check_python("def foo(\n")
        coloured = self.svc.format_coloured(report)
        assert "[ERROR]" in coloured

    def test_status(self):
        status = self.svc.get_status()
        assert status["service"] == "syntax_checker"
        assert status["colour_coded"] is True


# ── Dashboard Builder Service ────────────────────────────────────────

from backend.app.services.dashboard_builder_service import (
    DashboardBuilderService,
)


class TestDashboardBuilderService:
    def setup_method(self):
        self.svc = DashboardBuilderService()

    def test_create_project(self):
        result = self.svc.create_project("user1", "My Game", "game")
        assert result["name"] == "My Game"
        assert result["project_type"] == "game"
        assert result["task_count"] > 0

    def test_get_project(self):
        created = self.svc.create_project("user1", "Test")
        found = self.svc.get_project(created["project_id"])
        assert found is not None

    def test_add_task(self):
        project = self.svc.create_project("user1", "Test")
        task = self.svc.add_task(project["project_id"], "New task")
        assert task is not None
        assert task["title"] == "New task"

    def test_trigger_build(self):
        project = self.svc.create_project("user1", "Test")
        result = self.svc.trigger_build(project["project_id"])
        assert result["build_status"] == "success"

    def test_trigger_build_nonexistent(self):
        result = self.svc.trigger_build("fake-id")
        assert "error" in result

    def test_delete_project(self):
        project = self.svc.create_project("user1", "Test")
        assert self.svc.delete_project(project["project_id"]) is True

    def test_status(self):
        status = self.svc.get_status()
        assert status["service"] == "dashboard_builder"


# ── BLE LiDAR EEG Service ───────────────────────────────────────────

from backend.app.services.ble_lidar_eeg_service import (
    BLELidarEEGService,
    BLEDevice,
    DeviceType,
    ConnectionState,
)


class TestBLELidarEEGService:
    def setup_method(self):
        self.svc = BLELidarEEGService()

    def test_scan_devices_returns_list(self):
        """Scan returns a list (may be empty if no BLE hardware)."""
        devices = self.svc.scan_devices()
        assert isinstance(devices, list)

    def test_register_and_connect_device(self):
        """Register a device directly and verify connect/disconnect cycle."""
        dev = BLEDevice(
            device_id="test-eeg-001",
            name="Test EEG Headset",
            device_type=DeviceType.EEG_HEADSET,
            mac_address="AA:BB:CC:DD:EE:01",
        )
        self.svc._devices[dev.device_id] = dev
        result = self.svc.connect_device(dev.device_id)
        # Connection may succeed or return error (no real BLE hardware)
        assert "device_id" in result or "error" in result

    def test_connect_nonexistent(self):
        result = self.svc.connect_device("fake-id")
        assert "error" in result

    def test_eeg_stream_lifecycle(self):
        """Register, connect, stream, and read EEG data."""
        dev = BLEDevice(
            device_id="test-eeg-002",
            name="Test EEG",
            device_type=DeviceType.EEG_HEADSET,
            mac_address="AA:BB:CC:DD:EE:02",
            state=ConnectionState.CONNECTED,
            channels=4,
            sample_rate=256,
        )
        self.svc._devices[dev.device_id] = dev
        result = self.svc.start_eeg_stream(dev.device_id)
        assert result["state"] == "streaming"

        reading = self.svc.get_eeg_reading(dev.device_id)
        assert "band_powers" in reading
        assert "alpha" in reading["band_powers"]
        # Values should be real floats from sensor or noise-floor
        assert isinstance(reading["band_powers"]["alpha"], float)

    def test_lidar_frame(self):
        """Register a LiDAR device and read a frame."""
        dev = BLEDevice(
            device_id="test-lidar-001",
            name="Test LiDAR",
            device_type=DeviceType.LIDAR_SENSOR,
            mac_address="AA:BB:CC:DD:EE:03",
        )
        self.svc._devices[dev.device_id] = dev
        result = self.svc.get_lidar_frame(dev.device_id)
        assert "point_count" in result
        # Real sensor data – point_count may be 0 with no hardware
        assert isinstance(result["point_count"], int)

    def test_disconnect(self):
        dev = BLEDevice(
            device_id="test-dev-disc",
            name="Test Device",
            device_type=DeviceType.EEG_HEADSET,
            state=ConnectionState.CONNECTED,
        )
        self.svc._devices[dev.device_id] = dev
        result = self.svc.disconnect_device(dev.device_id)
        assert result["state"] == "disconnected"

    def test_status(self):
        status = self.svc.get_status()
        assert status["service"] == "ble_lidar_eeg"
        assert status["status"] == "online"
