"""
Organization API endpoints — multi-tenant workspace management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional  # noqa: F401 kept for future use

from app.dependencies import get_database, get_current_active_user
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationOut,
    OrganizationList,
    MembershipCreate,
    MembershipOut,
    MemberList,
    OrgProjectCreate,
    OrgProjectOut,
    OrgProjectList,
    ProjectPermissionCreate,
    ProjectPermissionOut,
)
from app.services import org_service
from app.services.audit_service import log_action

router = APIRouter()


# ── Organizations ──────────────────────────────────────────────────────────────

@router.get("/", response_model=OrganizationList)
async def list_organizations(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """List all organizations the current user belongs to."""
    orgs = org_service.list_orgs_for_user(db, current_user.id)
    return OrganizationList(items=orgs, total=len(orgs))


@router.post("/", response_model=OrganizationOut, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new organization. The creator becomes the owner."""
    org = org_service.create_org(db, data, owner_id=current_user.id)
    log_action(
        db,
        action="org.create",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="organization",
        resource_id=str(org.id),
        details={"name": org.name, "slug": org.slug},
    )
    return org


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(
    org_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    org = org_service.get_org(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.put("/{org_id}", response_model=OrganizationOut)
async def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    org = org_service.update_org(db, org_id, data, user_id=current_user.id)
    log_action(
        db,
        action="org.update",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="organization",
        resource_id=str(org_id),
    )
    return org


@router.delete("/{org_id}", status_code=204)
async def delete_organization(
    org_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    org_service.delete_org(db, org_id, user_id=current_user.id)
    log_action(
        db,
        action="org.delete",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="organization",
        resource_id=str(org_id),
    )


# ── Members ────────────────────────────────────────────────────────────────────

@router.get("/{org_id}/members", response_model=MemberList)
async def list_members(
    org_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    members = org_service.list_members(db, org_id)
    return MemberList(items=members, total=len(members))


@router.post("/{org_id}/members", response_model=MembershipOut, status_code=201)
async def add_member(
    org_id: int,
    data: MembershipCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    member = org_service.add_member(db, org_id, data, inviter_id=current_user.id)
    log_action(
        db,
        action="org.member.add",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="membership",
        resource_id=str(member.id),
        details={"user_id": data.user_id, "role": data.role},
    )
    return member


@router.delete("/{org_id}/members/{user_id}", status_code=204)
async def remove_member(
    org_id: int,
    user_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    org_service.remove_member(db, org_id, user_id, requester_id=current_user.id)
    log_action(
        db,
        action="org.member.remove",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="membership",
        details={"removed_user_id": user_id},
    )


# ── Projects ───────────────────────────────────────────────────────────────────

@router.get("/{org_id}/projects", response_model=OrgProjectList)
async def list_projects(
    org_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    projects = org_service.list_org_projects(db, org_id)
    return OrgProjectList(items=projects, total=len(projects))


@router.post("/{org_id}/projects", response_model=OrgProjectOut, status_code=201)
async def create_project(
    org_id: int,
    data: OrgProjectCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    project = org_service.create_org_project(db, org_id, data, creator_id=current_user.id)
    log_action(
        db,
        action="org.project.create",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="org_project",
        resource_id=str(project.id),
        details={"name": project.name, "org_id": org_id},
    )
    return project


@router.post(
    "/{org_id}/projects/{project_id}/permissions",
    response_model=ProjectPermissionOut,
    status_code=201,
)
async def add_project_permission(
    org_id: int,
    project_id: int,
    data: ProjectPermissionCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    perm = org_service.add_project_permission(
        db, project_id, data, granter_id=current_user.id
    )
    log_action(
        db,
        action="org.project.permission.grant",
        actor_id=current_user.id,
        resource_type="project_permission",
        resource_id=str(perm.id),
        details={"project_id": project_id, "user_id": data.user_id, "role": data.role},
    )
    return perm
