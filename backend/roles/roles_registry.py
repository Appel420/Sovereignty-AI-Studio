"""
Sovereignty AI Studio — Roles Registry
All role definitions for the permission/RBAC system.
Integrate via backend/api endpoints and middleware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional

# ---------------------------------------------------------------------------
# Role definition data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleDefinition:
    key: str                        # Unique slug used in DB / JWT
    label: str                      # Human-readable display name
    level: int                      # Clearance / seniority level (higher = more access)
    category: str                   # Org category (executive, legal, military, …)
    permissions: FrozenSet[str]     # Explicit permission grants
    inherits: FrozenSet[str] = field(default_factory=frozenset)  # Role keys inherited


# ---------------------------------------------------------------------------
# Permission constants
# ---------------------------------------------------------------------------

PERMS = frozenset([
    # Data access
    "data:read", "data:write", "data:delete", "data:export",
    # AI model access
    "ai:query", "ai:train", "ai:admin",
    # Org management
    "org:read", "org:write", "org:admin",
    # Project management
    "project:read", "project:write", "project:admin",
    # User management
    "user:read", "user:write", "user:admin",
    # Audit & compliance
    "audit:read", "audit:export", "audit:admin",
    # Security & intelligence
    "security:read", "security:write", "security:admin",
    # Government / legal
    "legal:read", "legal:write", "legal:admin",
    # Hardware / IoT
    "hardware:read", "hardware:write", "hardware:admin",
    # Financial
    "finance:read", "finance:write", "finance:admin",
    # Executive override
    "executive:override",
])

# ---------------------------------------------------------------------------
# Role registry — all roles defined here
# ---------------------------------------------------------------------------

ROLES: Dict[str, RoleDefinition] = {}


def _r(
    key: str,
    label: str,
    level: int,
    category: str,
    permissions: List[str],
    inherits: Optional[List[str]] = None,
) -> None:
    ROLES[key] = RoleDefinition(
        key=key,
        label=label,
        level=level,
        category=category,
        permissions=frozenset(permissions),
        inherits=frozenset(inherits or []),
    )


# ─── Viewer / Guest ───────────────────────────────────────────────────────
_r("viewer",       "Viewer",        level=0, category="general",
   permissions=["data:read", "ai:query", "org:read", "project:read"])

# ─── Standard member ──────────────────────────────────────────────────────
_r("member",       "Member",        level=1, category="general",
   permissions=["data:read", "data:write", "ai:query", "org:read",
                "project:read", "project:write"],
   inherits=["viewer"])

# ─── Project lead ─────────────────────────────────────────────────────────
_r("project_lead", "Project Lead",  level=2, category="general",
   permissions=["project:admin", "user:read"],
   inherits=["member"])

# ─── Analyst ──────────────────────────────────────────────────────────────
_r("analyst",      "Analyst",       level=2, category="intelligence",
   permissions=["data:read", "data:export", "ai:query", "audit:read",
                "security:read"],
   inherits=["member"])

# ─── Legal L5 ─────────────────────────────────────────────────────────────
_r("legal_l5",     "Legal L5",      level=5, category="legal",
   permissions=["legal:read", "legal:write", "legal:admin",
                "audit:read", "audit:export", "data:read", "data:export"],
   inherits=["analyst"])

# ─── Legal L4 ─────────────────────────────────────────────────────────────
_r("legal_l4",     "Legal L4",      level=4, category="legal",
   permissions=["legal:read", "legal:write", "audit:read", "data:read"],
   inherits=["member"])

# ─── Intelligence L5 ──────────────────────────────────────────────────────
_r("intelligence_l5", "Intelligence L5", level=5, category="intelligence",
   permissions=["security:read", "security:write", "security:admin",
                "audit:read", "audit:export", "data:read", "data:export",
                "ai:query", "ai:admin"],
   inherits=["analyst"])

# ─── Intelligence L4 ──────────────────────────────────────────────────────
_r("intelligence_l4", "Intelligence L4", level=4, category="intelligence",
   permissions=["security:read", "security:write", "audit:read",
                "data:read", "ai:query"],
   inherits=["member"])

# ─── Government L4 ────────────────────────────────────────────────────────
_r("government_l4", "Government L4", level=4, category="government",
   permissions=["legal:read", "audit:read", "audit:export",
                "data:read", "security:read"],
   inherits=["member"])

# ─── Military Operator ────────────────────────────────────────────────────
_r("military_operator", "Military Operator", level=4, category="military",
   permissions=["hardware:read", "hardware:write", "security:read",
                "data:read", "ai:query"],
   inherits=["member"])

# ─── Military Commander ───────────────────────────────────────────────────
_r("military_commander", "Military Commander", level=5, category="military",
   permissions=["hardware:admin", "security:admin", "data:read",
                "data:export", "ai:query", "ai:admin"],
   inherits=["military_operator"])

# ─── Finance ──────────────────────────────────────────────────────────────
_r("finance",      "Finance",       level=3, category="finance",
   permissions=["finance:read", "finance:write", "data:read", "audit:read"],
   inherits=["member"])

# ─── Finance Admin ────────────────────────────────────────────────────────
_r("finance_admin", "Finance Admin", level=4, category="finance",
   permissions=["finance:admin", "audit:export"],
   inherits=["finance"])

# ─── Org Admin ────────────────────────────────────────────────────────────
_r("org_admin",    "Org Admin",     level=4, category="general",
   permissions=["org:admin", "user:admin", "project:admin",
                "audit:read", "data:read", "data:write"],
   inherits=["project_lead"])

# ─── Security Admin ───────────────────────────────────────────────────────
_r("security_admin", "Security Admin", level=5, category="security",
   permissions=["security:admin", "audit:admin", "user:admin",
                "org:admin", "data:write"],
   inherits=["org_admin"])

# ─── Executive L5 (highest non-override clearance) ────────────────────────
_r("executive_l5", "Executive L5",  level=5, category="executive",
   permissions=list(PERMS - {"executive:override"}),
   inherits=["security_admin"])

# ─── System — full override (platform root) ───────────────────────────────
_r("system",       "System",        level=99, category="system",
   permissions=list(PERMS),
   inherits=["executive_l5"])


# ---------------------------------------------------------------------------
# RBAC helpers
# ---------------------------------------------------------------------------

def get_role(key: str) -> Optional[RoleDefinition]:
    """Return a RoleDefinition by key, or None if not found."""
    return ROLES.get(key)


def effective_permissions(role_key: str) -> FrozenSet[str]:
    """
    Return the full set of permissions for a role, including inherited roles.
    """
    seen: set = set()
    perms: set = set()

    def _collect(key: str) -> None:
        if key in seen:
            return
        seen.add(key)
        role = ROLES.get(key)
        if role is None:
            return
        perms.update(role.permissions)
        for parent in role.inherits:
            _collect(parent)

    _collect(role_key)
    return frozenset(perms)


def has_permission(role_key: str, permission: str) -> bool:
    """Check if a role (including inherited roles) has a specific permission."""
    return permission in effective_permissions(role_key)


def list_roles() -> List[Dict[str, object]]:
    """Return all roles as serialisable dicts (for the dashboard API)."""
    result = []
    for role in ROLES.values():
        result.append({
            "key": role.key,
            "label": role.label,
            "level": role.level,
            "category": role.category,
            "permissions": sorted(effective_permissions(role.key)),
            "inherits": sorted(role.inherits),
        })
    return sorted(result, key=lambda r: (r["category"], -r["level"]))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# RBAC middleware helper (framework-agnostic)
# ---------------------------------------------------------------------------

class RBACMiddleware:
    """
    Framework-agnostic RBAC check helper.

    Usage (FastAPI / Flask / raw):
        rbac = RBACMiddleware()
        rbac.require(user_role="member", permission="data:write")  # raises on fail
    """

    @staticmethod
    def require(user_role: str, permission: str) -> None:
        """
        Raise PermissionError if the user's role does not grant the permission.
        """
        if not has_permission(user_role, permission):
            raise PermissionError(
                f"Role '{user_role}' does not have permission '{permission}'."
            )

    @staticmethod
    def check(user_role: str, permission: str) -> bool:
        """Return True if the user's role grants the permission."""
        return has_permission(user_role, permission)
