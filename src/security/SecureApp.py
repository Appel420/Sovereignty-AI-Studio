"""Secure application module with JWT authentication and media persistence."""

from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
import redis
from jwt import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.config import settings
from app.core.database import Base

pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: Dict[str, str], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode: Dict[str, str] = data.copy()
    expire: datetime = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed counterpart."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash for the given password."""
    return pwd_context.hash(password)


def verify_token(token: str) -> Optional[str]:
    """Decode and validate a JWT token, returning username if valid."""
    try:
        payload: Dict[str, str] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload.get("sub")
    except InvalidTokenError:
        return None


redis_client: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis.Redis:
    """Return the singleton Redis client."""
    return redis_client


class Media(Base):
    """Media metadata persisted through SQLAlchemy."""

    __tablename__ = "media"

    id: int = Column(Integer, primary_key=True, index=True)
    filename: str = Column(String, nullable=False)
    original_filename: Optional[str] = Column(String, nullable=True)
    file_path: str = Column(String, nullable=False)
    file_url: Optional[str] = Column(String, nullable=True)
    file_type: str = Column(String, nullable=False)
    mime_type: str = Column(String, nullable=False)
    file_size: int = Column(BigInteger, nullable=False)
    width: Optional[int] = Column(Integer, nullable=True)
    height: Optional[int] = Column(Integer, nullable=True)
    duration: Optional[int] = Column(Integer, nullable=True)
    is_processed: bool = Column(Boolean, default=False)
    processing_status: str = Column(String, default="pending")
    title: Optional[str] = Column(String, nullable=True)
    description: Optional[str] = Column(Text, nullable=True)
    alt_text: Optional[str] = Column(String, nullable=True)
    storage_provider: str = Column(String, default="local")
    storage_bucket: Optional[str] = Column(String, nullable=True)
    storage_key: Optional[str] = Column(String, nullable=True)
    created_at: datetime = Column(DateTime, default=func.now())
    updated_at: datetime = Column(DateTime, default=func.now(), onupdate=func.now())
    project_id: Optional[int] = Column(Integer, ForeignKey("projects.id"), nullable=True)
    generation_id: Optional[int] = Column(Integer, ForeignKey("generations.id"), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Media id={self.id} filename={self.filename!r} "
            f"file_type={self.file_type!r} size={self.file_size}B "
            f"status={self.processing_status!r}>"
        )
