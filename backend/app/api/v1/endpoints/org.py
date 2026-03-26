"""FastAPI router for Organization management endpoints."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user, get_database
from app.models.org import Membership, Organization
from app.models.user import User
from app.schemas.org import (
    MemberCreate,
    MemberListResponse,
    MemberResponse,
    OrgCreate,
    OrgDetail,
    OrgListResponse,
    OrgResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_org_or_404(db: Session, org_id: int) -> Organization:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found",
        )
    return org


def _require_org_admin(
    db: Session, org_id: int, user: User
) -> Organization:
    """Raise 403 unless user is owner or admin of the org."""
    org = _get_org_or_404(db, org_id)
    membership = (
        db.query(Membership)
        .filter(
            Membership.org_id == org_id,
            Membership.user_id == user.id,
            Membership.role.in_(["owner", "admin"]),
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this organization",
        )
    return org


# ── Organization endpoints ────────────────────────────────────────────────────

@router.get("", response_model=OrgListResponse)
async def list_orgs(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> OrgListResponse:
    """List all organizations the current user belongs to."""
    memberships = (
        db.query(Membership)
        .filter(Membership.user_id == current_user.id)
        .all()
    )
    org_ids = [m.org_id for m in memberships]
    orgs: List[Organization] = (
        db.query(Organization)
        .filter(Organization.id.in_(org_ids))
        .all()
    )
    return OrgListResponse(
        orgs=[OrgResponse.model_validate(o) for o in orgs],
        total=len(orgs),
    )


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    payload: OrgCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> OrgResponse:
    """Create a new organization owned by the current user."""
    existing = (
        db.query(Organization)
        .filter(Organization.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization with that name already exists",
        )

    org = Organization(name=payload.name, owner_id=current_user.id)
    db.add(org)
    db.flush()

    # Auto-enroll creator as owner member
    membership = Membership(
        org_id=org.id, user_id=current_user.id, role="owner"
    )
    db.add(membership)
    db.commit()
    db.refresh(org)
    logger.info("Created org %d (%s) by user %d", org.id, org.name, current_user.id)
    return OrgResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrgDetail)
async def get_org(
    org_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> OrgDetail:
    """Get details for a specific organization."""
    org = _get_org_or_404(db, org_id)
    # Verify user is a member
    membership = (
        db.query(Membership)
        .filter(
            Membership.org_id == org_id,
            Membership.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    member_count = (
        db.query(Membership).filter(Membership.org_id == org_id).count()
    )
    return OrgDetail(
        **OrgResponse.model_validate(org).model_dump(),
        member_count=member_count,
    )


# ── Member endpoints ──────────────────────────────────────────────────────────

@router.get("/{org_id}/members", response_model=MemberListResponse)
async def list_members(
    org_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> MemberListResponse:
    """List all members of an organization."""
    _get_org_or_404(db, org_id)
    # Verify requester is a member
    membership = (
        db.query(Membership)
        .filter(
            Membership.org_id == org_id,
            Membership.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    members = (
        db.query(Membership).filter(Membership.org_id == org_id).all()
    )
    return MemberListResponse(
        members=[MemberResponse.model_validate(m) for m in members],
        total=len(members),
    )


@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    org_id: int,
    payload: MemberCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> MemberResponse:
    """Add a user to an organization with a specified role."""
    _require_org_admin(db, org_id, current_user)

    # Check target user exists
    target = db.query(User).filter(User.id == payload.user_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {payload.user_id} not found",
        )

    # Prevent duplicate memberships
    existing = (
        db.query(Membership)
        .filter(
            Membership.org_id == org_id,
            Membership.user_id == payload.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        )

    member = Membership(
        org_id=org_id, user_id=payload.user_id, role=payload.role
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    logger.info(
        "Added user %d to org %d as %s by user %d",
        payload.user_id,
        org_id,
        payload.role,
        current_user.id,
    )
    return MemberResponse.model_validate(member)
