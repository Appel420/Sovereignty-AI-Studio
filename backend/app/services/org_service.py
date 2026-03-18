"""
Organization service — business logic for multi-tenant org management.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.organization import Organization, Membership, OrgProject, ProjectPermission
from app.models.organization import OrgRole, ProjectRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    MembershipCreate,
    OrgProjectCreate,
    OrgProjectUpdate,
    ProjectPermissionCreate,
)


def get_org(db: Session, org_id: int) -> Optional[Organization]:
    return db.query(Organization).filter(Organization.id == org_id).first()


def get_org_by_slug(db: Session, slug: str) -> Optional[Organization]:
    return db.query(Organization).filter(Organization.slug == slug).first()


def list_orgs_for_user(db: Session, user_id: int) -> List[Organization]:
    """Return all orgs the user is a member of."""
    return (
        db.query(Organization)
        .join(Membership, Membership.organization_id == Organization.id)
        .filter(Membership.user_id == user_id, Membership.is_active.is_(True))
        .all()
    )


def create_org(db: Session, data: OrganizationCreate, owner_id: int) -> Organization:
    if get_org_by_slug(db, data.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization slug '{data.slug}' already exists",
        )
    org = Organization(**data.model_dump(), owner_id=owner_id)
    db.add(org)
    db.flush()
    # Auto-add owner as owner role
    membership = Membership(
        organization_id=org.id,
        user_id=owner_id,
        role=OrgRole.owner,
        invited_by=owner_id,
    )
    db.add(membership)
    try:
        db.commit()
        db.refresh(org)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create organization due to a conflict",
        )
    return org


def update_org(db: Session, org_id: int, data: OrganizationUpdate, user_id: int) -> Organization:
    org = _get_org_or_404(db, org_id)
    _require_role(db, org_id, user_id, {OrgRole.owner, OrgRole.admin})
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return org


def delete_org(db: Session, org_id: int, user_id: int) -> None:
    org = _get_org_or_404(db, org_id)
    _require_role(db, org_id, user_id, {OrgRole.owner})
    db.delete(org)
    db.commit()


# ── Members ────────────────────────────────────────────────────────────────────

def list_members(db: Session, org_id: int) -> List[Membership]:
    _get_org_or_404(db, org_id)
    return (
        db.query(Membership)
        .filter(Membership.organization_id == org_id, Membership.is_active.is_(True))
        .all()
    )


def add_member(
    db: Session, org_id: int, data: MembershipCreate, inviter_id: int
) -> Membership:
    _get_org_or_404(db, org_id)
    _require_role(db, org_id, inviter_id, {OrgRole.owner, OrgRole.admin})
    existing = (
        db.query(Membership)
        .filter(
            Membership.organization_id == org_id,
            Membership.user_id == data.user_id,
        )
        .first()
    )
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail="User is already a member")
        existing.is_active = True
        existing.role = data.role
        db.commit()
        db.refresh(existing)
        return existing
    m = Membership(
        organization_id=org_id,
        user_id=data.user_id,
        role=data.role,
        invited_by=inviter_id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def remove_member(db: Session, org_id: int, user_id: int, requester_id: int) -> None:
    _get_org_or_404(db, org_id)
    _require_role(db, org_id, requester_id, {OrgRole.owner, OrgRole.admin})
    m = (
        db.query(Membership)
        .filter(
            Membership.organization_id == org_id,
            Membership.user_id == user_id,
            Membership.is_active.is_(True),
        )
        .first()
    )
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    m.is_active = False
    db.commit()


# ── OrgProjects ────────────────────────────────────────────────────────────────

def list_org_projects(db: Session, org_id: int) -> List[OrgProject]:
    _get_org_or_404(db, org_id)
    return (
        db.query(OrgProject)
        .filter(OrgProject.organization_id == org_id, OrgProject.is_archived.is_(False))
        .all()
    )


def create_org_project(
    db: Session, org_id: int, data: OrgProjectCreate, creator_id: int
) -> OrgProject:
    _get_org_or_404(db, org_id)
    _require_role(db, org_id, creator_id, {OrgRole.owner, OrgRole.admin, OrgRole.member})
    project = OrgProject(
        organization_id=org_id,
        created_by=creator_id,
        **data.model_dump(),
    )
    db.add(project)
    db.flush()
    # Grant creator lead permissions
    perm = ProjectPermission(
        project_id=project.id,
        user_id=creator_id,
        role=ProjectRole.lead,
        granted_by=creator_id,
    )
    db.add(perm)
    db.commit()
    db.refresh(project)
    return project


def update_org_project(
    db: Session, project_id: int, data: OrgProjectUpdate, user_id: int
) -> OrgProject:
    project = _get_project_or_404(db, project_id)
    _require_project_role(db, project_id, user_id, {ProjectRole.lead})
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def add_project_permission(
    db: Session, project_id: int, data: ProjectPermissionCreate, granter_id: int
) -> ProjectPermission:
    _get_project_or_404(db, project_id)
    _require_project_role(db, project_id, granter_id, {ProjectRole.lead})
    existing = (
        db.query(ProjectPermission)
        .filter(
            ProjectPermission.project_id == project_id,
            ProjectPermission.user_id == data.user_id,
        )
        .first()
    )
    if existing:
        existing.role = data.role
        db.commit()
        db.refresh(existing)
        return existing
    perm = ProjectPermission(
        project_id=project_id,
        user_id=data.user_id,
        role=data.role,
        granted_by=granter_id,
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


# ── Internal helpers ───────────────────────────────────────────────────────────

def _get_org_or_404(db: Session, org_id: int) -> Organization:
    org = get_org(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _get_project_or_404(db: Session, project_id: int) -> OrgProject:
    project = db.query(OrgProject).filter(OrgProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_role(
    db: Session, org_id: int, user_id: int, allowed: set
) -> Membership:
    m = (
        db.query(Membership)
        .filter(
            Membership.organization_id == org_id,
            Membership.user_id == user_id,
            Membership.is_active.is_(True),
        )
        .first()
    )
    if not m or m.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient organization permissions")
    return m


def _require_project_role(
    db: Session, project_id: int, user_id: int, allowed: set
) -> ProjectPermission:
    perm = (
        db.query(ProjectPermission)
        .filter(
            ProjectPermission.project_id == project_id,
            ProjectPermission.user_id == user_id,
        )
        .first()
    )
    if not perm or perm.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient project permissions")
    return perm
