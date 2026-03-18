"""Pydantic schemas for Organization and Membership."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Organization schemas ─────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrgResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    owner_id: int

    class Config:
        from_attributes = True


class OrgDetail(OrgResponse):
    member_count: Optional[int] = 0


# ── Membership schemas ───────────────────────────────────────────────────────

class MemberCreate(BaseModel):
    user_id: int
    role: str = Field("member", pattern="^(owner|admin|member)$")


class MemberResponse(BaseModel):
    id: int
    org_id: int
    user_id: int
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class OrgListResponse(BaseModel):
    orgs: List[OrgResponse]
    total: int


class MemberListResponse(BaseModel):
    members: List[MemberResponse]
    total: int
