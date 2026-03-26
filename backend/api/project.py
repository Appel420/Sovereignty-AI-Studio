"""
Sovereignty AI Studio — Project API
CRUD operations for projects and per-project permission management.
"""

from __future__ import annotations

from typing import List, Optional

from db.connector import execute, execute_one, execute_write


# ──────────────────────────────────────────────────────────────────────────
# Project CRUD
# ──────────────────────────────────────────────────────────────────────────

def create_project(
    org_id: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    row = execute_one(
        """
        INSERT INTO projects (org_id, name, description)
        VALUES (%s, %s, %s)
        RETURNING *
        """,
        (org_id, name, description),
    )
    if row is None:
        raise RuntimeError("Failed to create project")
    return dict(row)


def get_project(project_id: str) -> Optional[dict]:
    row = execute_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    return dict(row) if row else None


def list_projects(org_id: str, limit: int = 100, offset: int = 0) -> List[dict]:
    return [dict(r) for r in execute(
        """
        SELECT * FROM projects WHERE org_id = %s
        ORDER BY created_at DESC LIMIT %s OFFSET %s
        """,
        (org_id, limit, offset),
    )]


def update_project(
    project_id: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[dict]:
    updates: list = []
    params: list = []
    if name is not None:
        updates.append("name = %s")
        params.append(name)
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if not updates:
        return get_project(project_id)
    updates.append("updated_at = NOW()")
    params.append(project_id)
    row = execute_one(
        f"UPDATE projects SET {', '.join(updates)} WHERE id = %s RETURNING *",
        tuple(params),
    )
    return dict(row) if row else None


def delete_project(project_id: str) -> bool:
    n = execute_write("DELETE FROM projects WHERE id = %s", (project_id,))
    return n > 0


# ──────────────────────────────────────────────────────────────────────────
# Project permissions
# ──────────────────────────────────────────────────────────────────────────

def grant_permission(project_id: str, user_id: str, role: str = "viewer") -> dict:
    row = execute_one(
        """
        INSERT INTO project_permissions (project_id, user_id, role)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, project_id) DO UPDATE SET role = EXCLUDED.role
        RETURNING *
        """,
        (project_id, user_id, role),
    )
    if row is None:
        raise RuntimeError("Failed to grant permission")
    return dict(row)


def revoke_permission(project_id: str, user_id: str) -> bool:
    n = execute_write(
        "DELETE FROM project_permissions WHERE project_id = %s AND user_id = %s",
        (project_id, user_id),
    )
    return n > 0


def list_permissions(project_id: str) -> List[dict]:
    return [dict(r) for r in execute(
        """
        SELECT u.id, u.email, u.display_name, pp.role, pp.granted_at
        FROM project_permissions pp
        JOIN users u ON u.id = pp.user_id
        WHERE pp.project_id = %s
        ORDER BY pp.granted_at
        """,
        (project_id,),
    )]


def get_user_role(project_id: str, user_id: str) -> Optional[str]:
    row = execute_one(
        "SELECT role FROM project_permissions WHERE project_id = %s AND user_id = %s",
        (project_id, user_id),
    )
    return row["role"] if row else None
