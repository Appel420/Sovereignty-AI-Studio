import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import pytest
from fastapi import HTTPException

from app import dependencies


def test_get_database_returns_first_session(monkeypatch):
    sentinel = object()

    def fake_get_db():
        yield sentinel

    monkeypatch.setattr(dependencies, "get_db", fake_get_db)

    assert dependencies.get_database() is sentinel


@pytest.mark.asyncio
async def test_get_current_user_returns_lookup_result(monkeypatch):
    user = SimpleNamespace(username="ada", is_active=True)
    credentials = SimpleNamespace(credentials="signed-token")

    monkeypatch.setattr(dependencies, "verify_token", lambda token: "ada")
    monkeypatch.setattr(
        dependencies,
        "get_user_by_username",
        lambda db, username: user if username == "ada" else None,
    )

    result = await dependencies.get_current_user(credentials=credentials, db=object())

    assert result is user


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("token_result", "lookup_result", "status_code"),
    [
        (None, None, 401),
        ("ada", None, 401),
    ],
)
async def test_get_current_user_rejects_invalid_auth(
    monkeypatch,
    token_result,
    lookup_result,
    status_code,
):
    credentials = SimpleNamespace(credentials="signed-token")

    monkeypatch.setattr(dependencies, "verify_token", lambda token: token_result)
    monkeypatch.setattr(
        dependencies,
        "get_user_by_username",
        lambda db, username: lookup_result,
    )

    with pytest.raises(HTTPException) as excinfo:
        await dependencies.get_current_user(credentials=credentials, db=object())

    assert excinfo.value.status_code == status_code
    assert excinfo.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_active_user_rejects_inactive_user():
    current_user = SimpleNamespace(is_active=False)

    with pytest.raises(HTTPException) as excinfo:
        await dependencies.get_current_active_user(current_user=current_user)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Inactive user"


@pytest.mark.asyncio
async def test_get_optional_user_handles_missing_or_invalid_credentials(monkeypatch):
    credentials = SimpleNamespace(credentials="signed-token")
    user = SimpleNamespace(username="ada", is_active=True)

    monkeypatch.setattr(dependencies, "verify_token", lambda token: "ada")
    monkeypatch.setattr(
        dependencies,
        "get_user_by_username",
        lambda db, username: user if username == "ada" else None,
    )

    assert await dependencies.get_optional_user(credentials=None, db=object()) is None
    assert await dependencies.get_optional_user(credentials=credentials, db=object()) is user


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_for_invalid_token(monkeypatch):
    credentials = SimpleNamespace(credentials="bad-token")

    monkeypatch.setattr(dependencies, "verify_token", lambda token: None)

    assert await dependencies.get_optional_user(credentials=credentials, db=object()) is None
