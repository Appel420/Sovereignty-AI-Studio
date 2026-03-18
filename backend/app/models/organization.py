"""
Organization, Membership, OrgProject, and ProjectPermission SQLAlchemy models.
Multi-tenant workspace support with org → projects → members hierarchy.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class OrgRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class ProjectRole(str, enum.Enum):
    lead = "lead"
    contributor = "contributor"
    viewer = "viewer"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    website = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    plan = Column(String(50), default="free")  # free, pro, enterprise

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # owner user id (denormalized for quick lookup)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    memberships = relationship(
        "Membership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    org_projects = relationship(
        "OrgProject",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(
        SAEnum(OrgRole, name="orgrole"),
        nullable=False,
        default=OrgRole.member,
    )
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    joined_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="memberships")


class OrgProject(Base):
    """Projects that belong to an organization (separate from personal projects)."""
    __tablename__ = "org_projects"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(String(50), default="general")
    status = Column(String(50), default="active")
    is_archived = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="org_projects")
    permissions = relationship(
        "ProjectPermission",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectPermission(Base):
    __tablename__ = "project_permissions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("org_projects.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(
        SAEnum(ProjectRole, name="projectrole"),
        nullable=False,
        default=ProjectRole.viewer,
    )
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=func.now())

    project = relationship("OrgProject", back_populates="permissions")
