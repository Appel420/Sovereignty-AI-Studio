"""
Plugin manager — dynamic plugin loading, lifecycle management, and health monitoring.
"""
import importlib
import logging
import os
import sys
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.plugin import Plugin

# Ensure the repo root is on sys.path so `plugins.sdk` can be resolved
# whether the backend is run from `backend/` or from the repo root.
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_repo_root = os.path.dirname(_backend_dir)
for _path in (_repo_root, _backend_dir):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from plugins.sdk.plugin_base import PluginBase  # noqa: E402

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages the plugin registry and lifecycle."""

    def __init__(self):
        self._loaded: Dict[str, PluginBase] = {}

    def list_plugins(self, db: Session, status: Optional[str] = None) -> List[Plugin]:
        q = db.query(Plugin)
        if status:
            q = q.filter(Plugin.status == status)
        return q.order_by(Plugin.name).all()

    def get_plugin(self, db: Session, name: str) -> Optional[Plugin]:
        return db.query(Plugin).filter(Plugin.name == name).first()

    def install(
        self,
        db: Session,
        name: str,
        display_name: str,
        version: str,
        entry_point: str,
        description: Optional[str] = None,
        author: Optional[str] = None,
        category: Optional[str] = None,
        config_schema: Optional[dict] = None,
        default_config: Optional[dict] = None,
    ) -> Plugin:
        existing = self.get_plugin(db, name)
        if existing:
            existing.version = version
            existing.entry_point = entry_point
            existing.status = "inactive"
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        plugin = Plugin(
            name=name,
            display_name=display_name,
            version=version,
            entry_point=entry_point,
            description=description,
            author=author,
            category=category,
            config_schema=config_schema,
            default_config=default_config,
            status="inactive",
            is_enabled=False,
        )
        db.add(plugin)
        db.commit()
        db.refresh(plugin)
        return plugin

    def uninstall(self, db: Session, name: str) -> bool:
        plugin = self.get_plugin(db, name)
        if not plugin:
            return False
        if name in self._loaded:
            try:
                self._loaded[name].stop()
            except Exception:
                pass
            del self._loaded[name]
        db.delete(plugin)
        db.commit()
        return True

    def activate(self, db: Session, name: str, config: Optional[dict] = None) -> Plugin:
        plugin = self.get_plugin(db, name)
        if not plugin:
            raise ValueError(f"Plugin '{name}' not found")
        instance = self._load_instance(plugin, config or plugin.default_config or {})
        instance.configure(config or plugin.default_config or {})
        self._loaded[name] = instance
        plugin.status = "active"
        plugin.is_enabled = True
        db.commit()
        db.refresh(plugin)
        return plugin

    def deactivate(self, db: Session, name: str) -> Plugin:
        plugin = self.get_plugin(db, name)
        if not plugin:
            raise ValueError(f"Plugin '{name}' not found")
        if name in self._loaded:
            try:
                self._loaded[name].stop()
            except Exception:
                pass
            del self._loaded[name]
        plugin.status = "inactive"
        plugin.is_enabled = False
        db.commit()
        db.refresh(plugin)
        return plugin

    def run_plugin(self, name: str, payload: dict) -> Any:
        instance = self._loaded.get(name)
        if not instance:
            raise RuntimeError(f"Plugin '{name}' is not active")
        return instance.run(payload)

    def health_check_all(self, db: Session) -> dict:
        results = {}
        for name, instance in self._loaded.items():
            try:
                healthy = instance.health_check()
                results[name] = {"healthy": healthy}
                plugin = self.get_plugin(db, name)
                if plugin:
                    plugin.health_status = "ok" if healthy else "degraded"
                    plugin.last_health_check = datetime.utcnow()
                    db.commit()
            except Exception as exc:
                results[name] = {"healthy": False, "error": str(exc)}
        return results

    def _load_instance(self, plugin: Plugin, config: dict) -> PluginBase:
        """Dynamically import and instantiate a plugin class."""
        try:
            module_path, class_name = plugin.entry_point.rsplit(":", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls(config=config)
        except Exception as exc:
            logger.error("Failed to load plugin %s: %s", plugin.name, exc)
            raise RuntimeError(f"Cannot load plugin '{plugin.name}': {exc}") from exc


# Module-level singleton
plugin_manager = PluginManager()
