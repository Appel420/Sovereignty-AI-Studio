"""Tests for the user status (online/offline) feature.

Covers the UserStatus enum, UserStatusUpdate / UserStatusResponse schemas,
the update_user_status service function, and model field verification.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required env vars before any backend import triggers Settings()
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")


# ── Schema tests ─────────────────────────────────────────────────────

from backend.app.schemas.user import (
    UserStatus,
    UserStatusUpdate,
    UserStatusResponse,
    UserInDB,
)


class TestUserStatusEnum:
    def test_online_value(self):
        assert UserStatus.online == "online"

    def test_offline_value(self):
        assert UserStatus.offline == "offline"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValueError):
            UserStatus("busy")


class TestUserStatusUpdateSchema:
    def test_valid_online(self):
        obj = UserStatusUpdate(status=UserStatus.online)
        assert obj.status == UserStatus.online

    def test_valid_offline(self):
        obj = UserStatusUpdate(status=UserStatus.offline)
        assert obj.status == UserStatus.offline

    def test_from_string(self):
        obj = UserStatusUpdate(status="online")
        assert obj.status == UserStatus.online

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            UserStatusUpdate(status="invisible")


class TestUserStatusResponseSchema:
    def test_basic_fields(self):
        now = datetime.utcnow()
        resp = UserStatusResponse(
            user_id=1,
            username="alice",
            status="online",
            last_seen=now,
        )
        assert resp.user_id == 1
        assert resp.username == "alice"
        assert resp.status == "online"
        assert resp.last_seen == now

    def test_last_seen_optional(self):
        resp = UserStatusResponse(
            user_id=2,
            username="bob",
            status="offline",
        )
        assert resp.last_seen is None


class TestUserInDBStatusDefaults:
    def test_default_status_offline(self):
        now = datetime.utcnow()
        user = UserInDB(
            id=1,
            email="a@b.com",
            username="alice",
            is_active=True,
            is_verified=False,
            subscription_plan="free",
            subscription_expires_at=None,
            total_generations=0,
            monthly_generations=0,
            created_at=now,
            updated_at=now,
            last_login=None,
        )
        assert user.status == "offline"
        assert user.last_seen is None


# ── Service tests ────────────────────────────────────────────────────

from backend.app.services.user_service import update_user_status
# Re-use the User model already imported via the service module
from app.models.user import User as UserModel


class TestUpdateUserStatusService:
    def _make_mock_user(self, user_id=1, username="alice", status="offline"):
        user = MagicMock()
        user.id = user_id
        user.username = username
        user.status = status
        user.last_seen = None
        return user

    def test_update_to_online(self):
        mock_user = self._make_mock_user()
        db = MagicMock()

        with patch(
            "backend.app.services.user_service.get_user_by_id",
            return_value=mock_user,
        ):
            result = update_user_status(db, 1, UserStatus.online)

        assert result is not None
        assert mock_user.status == "online"
        assert mock_user.last_seen is not None
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_user)

    def test_update_to_offline(self):
        mock_user = self._make_mock_user(status="online")
        db = MagicMock()

        with patch(
            "backend.app.services.user_service.get_user_by_id",
            return_value=mock_user,
        ):
            result = update_user_status(db, 1, UserStatus.offline)

        assert result is not None
        assert mock_user.status == "offline"

    def test_user_not_found_returns_none(self):
        db = MagicMock()

        with patch(
            "backend.app.services.user_service.get_user_by_id",
            return_value=None,
        ):
            result = update_user_status(db, 999, UserStatus.online)

        assert result is None
        db.commit.assert_not_called()


# ── Model field tests ────────────────────────────────────────────────


class TestUserModelFields:
    def test_status_column_exists(self):
        assert hasattr(UserModel, "status")

    def test_last_seen_column_exists(self):
        assert hasattr(UserModel, "last_seen")

    def test_status_default(self):
        col = UserModel.__table__.columns["status"]
        assert col.default.arg == "offline"
