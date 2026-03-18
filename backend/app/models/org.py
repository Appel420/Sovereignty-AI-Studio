"""SQLAlchemy models for Organization and Membership."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Organization(Base):
    """Represents a tenant organization in the platform."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    memberships = relationship(
        "Membership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class Membership(Base):
    """Associates a User with an Organization and assigns a role."""

    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # role: owner | admin | member
    role = Column(String(50), nullable=False, default="member")
    joined_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id])
