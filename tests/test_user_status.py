"""Tests for the user status (online/offline) feature.

Uses a real in-memory SQLite database – no mocks.

Covers the UserStatus enum, UserStatusUpdate / UserStatusResponse schemas,
the update_user_status service function, and model field verification.
"""
import os
import sys
import pytest
from datetime import datetime, timezone

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
        now = datetime.now(timezone.utc)
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
        now = datetime.now(timezone.utc)
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


# ── Service tests (real in-memory SQLite) ────────────────────────────

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User as UserModel
from backend.app.services.user_service import update_user_status
from app.core.security import get_password_hash


@pytest.fixture()
def db_session():
    """Create a real in-memory SQLite database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    # Import ALL models so SQLAlchemy can resolve cross-model relationships
    import app.models.user        # noqa: F401
    import app.models.project     # noqa: F401
    import app.models.generation  # noqa: F401
    import app.models.alert       # noqa: F401
    import app.models.media       # noqa: F401
    import app.models.session     # noqa: F401
    import app.models.audit_log   # noqa: F401
    import app.models.plugin      # noqa: F401
    import app.models.usage       # noqa: F401
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def sample_user(db_session):
    """Insert a real user row into the test database."""
    user = UserModel(
        email="alice@example.com",
        username="alice",
        full_name="Alice Test",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        status="offline",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestUpdateUserStatusService:
    def test_update_to_online(self, db_session, sample_user):
        result = update_user_status(db_session, sample_user.id, UserStatus.online)

        assert result is not None
        assert result.status == "online"
        assert result.last_seen is not None

    def test_update_to_offline(self, db_session, sample_user):
        # First go online
        update_user_status(db_session, sample_user.id, UserStatus.online)
        online_last_seen = sample_user.last_seen

        # Then go offline
        result = update_user_status(db_session, sample_user.id, UserStatus.offline)
        assert result is not None
        assert result.status == "offline"
        # last_seen should NOT be updated when going offline
        assert result.last_seen == online_last_seen

    def test_user_not_found_returns_none(self, db_session):
        result = update_user_status(db_session, 999, UserStatus.online)
        assert result is None


# ── Model field tests ────────────────────────────────────────────────


class TestUserModelFields:
    def test_status_column_exists(self):
        assert hasattr(UserModel, "status")

    def test_last_seen_column_exists(self):
        assert hasattr(UserModel, "last_seen")

    def test_status_default(self):
        col = UserModel.__table__.columns["status"]
        assert col.default.arg == "offline"
