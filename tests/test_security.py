import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from app.core.security import get_password_hash, verify_password


def test_password_hash_round_trip():
    password = "password123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)


def test_password_hash_round_trip_for_long_password():
    password = "p" * 128
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
