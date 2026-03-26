"""
Sovereignty AI Studio — Org API
CRUD operations for organisations and membership management.
"""

from __future__ import annotations

from typing import List, Optional

from db.connector import execute, execute_one, execute_write


# ──────────────────────────────────────────────────────────────────────────
# Organisation CRUD
# ──────────────────────────────────────────────────────────────────────────

def create_org(name: str, slug: Optional[str] = None, plan: str = "standard") -> dict:
    row = execute_one(
        """
        INSERT INTO organizations (name, slug, plan)
        VALUES (%s, %s, %s)
        RETURNING *
        """,
        (name, slug, plan),
    )
    if row is None:
        raise RuntimeError("Failed to create organisation")
    return dict(row)


def get_org(org_id: str) -> Optional[dict]:
    row = execute_one(
        "SELECT * FROM organizations WHERE id = %s",
        (org_id,),
    )
    return dict(row) if row else None


def list_orgs(limit: int = 100, offset: int = 0) -> List[dict]:
    return [dict(r) for r in execute(
        "SELECT * FROM organizations ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )]


def update_org(
    org_id: str, *, name: Optional[str] = None, plan: Optional[str] = None
) -> Optional[dict]:
    updates: list = []
    params: list = []
    if name is not None:
        updates.append("name = %s")
        params.append(name)
    if plan is not None:
        updates.append("plan = %s")
        params.append(plan)
    if not updates:
        return get_org(org_id)
    updates.append("updated_at = NOW()")
    params.append(org_id)
    row = execute_one(
        f"UPDATE organizations SET {', '.join(updates)} WHERE id = %s RETURNING *",
        tuple(params),
    )
    return dict(row) if row else None


def delete_org(org_id: str) -> bool:
    n = execute_write("DELETE FROM organizations WHERE id = %s", (org_id,))
    return n > 0


# ──────────────────────────────────────────────────────────────────────────
# Membership management
# ──────────────────────────────────────────────────────────────────────────

def add_member(org_id: str, user_id: str, role: str = "member") -> dict:
    row = execute_one(
        """
        INSERT INTO memberships (org_id, user_id, role)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, org_id) DO UPDATE SET role = EXCLUDED.role
        RETURNING *
        """,
        (org_id, user_id, role),
    )
    if row is None:
        raise RuntimeError("Failed to add member")
    return dict(row)


def remove_member(org_id: str, user_id: str) -> bool:
    n = execute_write(
        "DELETE FROM memberships WHERE org_id = %s AND user_id = %s",
        (org_id, user_id),
    )
    return n > 0


def list_members(org_id: str) -> List[dict]:
    return [dict(r) for r in execute(
        """
        SELECT u.id, u.email, u.display_name, m.role, m.joined_at
        FROM memberships m
        JOIN users u ON u.id = m.user_id
        WHERE m.org_id = %s
        ORDER BY m.joined_at
        """,
        (org_id,),
    )]


def get_membership(org_id: str, user_id: str) -> Optional[dict]:
    row = execute_one(
        "SELECT * FROM memberships WHERE org_id = %s AND user_id = %s",
        (org_id, user_id),
    )
    return dict(row) if row else None
