"""
Marketplace API endpoints — browse, install, and remove agent plugins.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.dependencies import get_database, get_current_active_user
from app.models.user import User
from app.services.plugin_manager import plugin_manager
from app.services.audit_service import log_action

router = APIRouter()


class InstallRequest(BaseModel):
    name: str
    display_name: str
    version: str
    entry_point: str
    description: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    config_schema: Optional[dict] = None
    default_config: Optional[dict] = None


class ActivateRequest(BaseModel):
    config: Optional[dict] = None


@router.get("/")
async def list_marketplace_plugins(
    status: Optional[str] = None,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """List all installed plugins, optionally filtered by status."""
    plugins = plugin_manager.list_plugins(db, status=status)
    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "category": p.category,
                "status": p.status,
                "is_enabled": p.is_enabled,
                "health_status": p.health_status,
                "installed_at": p.installed_at.isoformat() if p.installed_at else None,
            }
            for p in plugins
        ],
        "total": len(plugins),
    }


@router.post("/install", status_code=201)
async def install_plugin(
    data: InstallRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """Register and install a plugin from its entry point."""
    plugin = plugin_manager.install(
        db,
        name=data.name,
        display_name=data.display_name,
        version=data.version,
        entry_point=data.entry_point,
        description=data.description,
        author=data.author,
        category=data.category,
        config_schema=data.config_schema,
        default_config=data.default_config,
    )
    log_action(
        db,
        action="marketplace.install",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="plugin",
        resource_id=str(plugin.id),
        details={"name": data.name, "version": data.version},
    )
    return {
        "id": plugin.id,
        "name": plugin.name,
        "status": plugin.status,
        "message": f"Plugin '{plugin.name}' installed successfully",
    }


@router.post("/{plugin_name}/activate")
async def activate_plugin(
    plugin_name: str,
    data: ActivateRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """Activate (load) an installed plugin."""
    try:
        plugin = plugin_manager.activate(db, plugin_name, config=data.config)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    log_action(
        db,
        action="marketplace.activate",
        actor_id=current_user.id,
        resource_type="plugin",
        resource_id=str(plugin.id),
    )
    return {"name": plugin.name, "status": plugin.status}


@router.delete("/uninstall/{plugin_name}", status_code=204)
async def uninstall_plugin(
    plugin_name: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """Deactivate and remove a plugin."""
    removed = plugin_manager.uninstall(db, plugin_name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    log_action(
        db,
        action="marketplace.uninstall",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="plugin",
        details={"name": plugin_name},
    )


@router.get("/health")
async def plugins_health(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
):
    """Run health checks on all active plugins."""
    return plugin_manager.health_check_all(db)
