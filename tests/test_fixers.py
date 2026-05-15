"""
Tests for fixers module.
"""

import asyncio
import pytest
from pathlib import Path
import tempfile
import shutil

from fixers.config_fixer import ConfigFixer
from fixers.model_fixer import ModelFixer
from errors.exceptions import AIModelError


class TestConfigFixer:
    """Test configuration fixer."""

    def test_validate_config_valid(self):
        fixer = ConfigFixer()
        config = {
            "SG_PORT": 9897,
            "SG_HOST": "localhost",
            "MAX_CLIENTS": 100,
        }
        is_valid, issues = fixer.validate_config(config)
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_config_invalid_port(self):
        fixer = ConfigFixer()
        config = {"SG_PORT": 99999}  # Invalid port
        is_valid, issues = fixer.validate_config(config)
        assert is_valid is False
        assert len(issues) > 0

    def test_fix_config(self):
        fixer = ConfigFixer()
        config = {"SG_PORT": 99999}  # Invalid port
        fixed = fixer.fix_config(config)
        assert fixed["SG_PORT"] == 9897  # Default value


class TestModelFixer:
    """Test model fixer."""

    def test_register_fallback(self):
        fixer = ModelFixer()
        fixer.register_fallback("claude", "gpt")
        assert fixer.get_fallback_model("claude") == "gpt"

    def test_get_fallback_model_family(self):
        fixer = ModelFixer()
        fallback = fixer.get_fallback_model("claude-3-opus")
        assert fallback is not None
        assert "gpt" in fallback.lower()

    def test_fix_model_selection(self):
        fixer = ModelFixer()
        available = ["gpt-4", "gpt-3.5-turbo"]

        # Test exact match
        model = fixer.fix_model_selection("gpt-4", available)
        assert model == "gpt-4"

        # Test fallback
        model = fixer.fix_model_selection("claude", available)
        assert model in available

    def test_fix_model_selection_no_match(self):
        fixer = ModelFixer()
        with pytest.raises(AIModelError):
            fixer.fix_model_selection("unknown-model", [])

    def test_mark_model_failed(self):
        fixer = ModelFixer()
        fixer.mark_model_failed("claude-3")
        assert fixer.is_model_failed("claude-3") is True
        assert fixer.is_model_failed("Claude-3") is True  # Case insensitive

    def test_validate_model_name(self):
        fixer = ModelFixer()
        assert fixer.validate_model_name("claude-3-opus") is True
        assert fixer.validate_model_name("gpt_4") is True
        assert fixer.validate_model_name("invalid@model") is False
        assert fixer.validate_model_name("") is False

    def test_fix_model_name(self):
        fixer = ModelFixer()
        fixed = fixer.fix_model_name("claude@3#opus")
        assert fixed == "claude3opus"

    def test_fix_model_name_invalid(self):
        fixer = ModelFixer()
        with pytest.raises(AIModelError):
            fixer.fix_model_name("@@@")

    def test_get_model_family(self):
        fixer = ModelFixer()
        assert fixer.get_model_family("claude-3-opus") == "claude"
        assert fixer.get_model_family("gpt-4") == "gpt"
        assert fixer.get_model_family("grok-1") == "grok"
        assert fixer.get_model_family("qwen-2-72b") == "qwen"
        assert fixer.get_model_family("unknown-model") == "unknown"

    def test_reset_failed_models(self):
        fixer = ModelFixer()
        fixer.mark_model_failed("claude-3")
        fixer.mark_model_failed("gpt-4")
        assert len(fixer._failed_models) == 2

        fixer.reset_failed_models()
        assert len(fixer._failed_models) == 0


class TestDatabaseFixer:
    """Test database fixer."""

    @pytest.mark.asyncio
    async def test_rebuild_database(self):
        # Create temporary database
        temp_dir = Path(tempfile.mkdtemp())
        db_path = temp_dir / "test.db"
        schema = """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        );
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        );
        """

        try:
            from fixers.database_fixer import DatabaseFixer

            fixer = DatabaseFixer(db_path, schema)

            # Rebuild database
            success = fixer.rebuild_database()
            assert success is True
            assert db_path.exists()

            # Check integrity
            is_healthy, issues = fixer.check_integrity()
            assert is_healthy is True
            assert issues == []

        finally:
            # Cleanup
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
