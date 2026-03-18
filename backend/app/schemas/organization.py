"""
Pydantic schemas for Organization, Membership, OrgProject, and ProjectPermission.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.organization import OrgRole, ProjectRole


# ── Organization ───────────────────────────────────────────────────────────────
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None


class OrganizationOut(OrganizationBase):
    id: int
    owner_id: int
    is_active: bool
    plan: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Membership ─────────────────────────────────────────────────────────────────
class MembershipCreate(BaseModel):
    user_id: int
    role: OrgRole = OrgRole.member


class MembershipUpdate(BaseModel):
    role: OrgRole


class MembershipOut(BaseModel):
    id: int
    organization_id: int
    user_id: int
    role: OrgRole
    is_active: bool
    joined_at: datetime

    class Config:
        from_attributes = True


# ── OrgProject ─────────────────────────────────────────────────────────────────
class OrgProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_type: str = "general"


class OrgProjectCreate(OrgProjectBase):
    pass


class OrgProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    is_archived: Optional[bool] = None


class OrgProjectOut(OrgProjectBase):
    id: int
    organization_id: int
    status: str
    is_archived: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── ProjectPermission ──────────────────────────────────────────────────────────
class ProjectPermissionCreate(BaseModel):
    user_id: int
    role: ProjectRole = ProjectRole.viewer


class ProjectPermissionOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: ProjectRole
    granted_at: datetime

    class Config:
        from_attributes = True


# ── Summary list responses ─────────────────────────────────────────────────────
class OrganizationList(BaseModel):
    items: List[OrganizationOut]
    total: int


class MemberList(BaseModel):
    items: List[MembershipOut]
    total: int


class OrgProjectList(BaseModel):
    items: List[OrgProjectOut]
    total: int
