"""Plugin Agent — hot-loads and executes plugins from the plugin_sdk directory.

Plugins are discovered by scanning for directories inside ``plugin_sdk/`` that
contain a valid ``plugin.json`` manifest.  Each plugin is executed under Judge
supervision so that resource conflicts are avoided.

Plugin manifest (``plugin.json``) schema::

    {
        "id":          "unique_plugin_id",
        "name":        "Human Readable Name",
        "version":     "1.0.0",
        "entry":       "main.py",
        "description": "What this plugin does"
    }
"""

import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_PLUGIN_SDK_DIR = Path(os.getenv("PLUGIN_SDK_DIR", "plugin_sdk"))


def _load_manifest(plugin_dir: Path) -> Optional[Dict[str, Any]]:
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path) as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("Invalid manifest in %s: %s", plugin_dir, exc)
        return None


def _load_plugin_module(plugin_dir: Path, entry: str) -> Any:
    """Dynamically import the plugin's entry-point module."""
    entry_path = plugin_dir / entry
    if not entry_path.exists():
        raise FileNotFoundError(f"Plugin entry '{entry_path}' not found")
    spec = importlib.util.spec_from_file_location(
        str(plugin_dir.name), entry_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {entry_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class PluginAgent:
    """Discovers, loads, and runs plugins under Judge supervision."""

    AGENT_ID = "plugin_agent"

    def __init__(self, judge: Any) -> None:
        self._judge = judge
        self._plugins: Dict[str, Dict[str, Any]] = {}

    def discover(self) -> List[str]:
        """Scan ``plugin_sdk/`` for valid plugin directories.

        Returns:
            List of discovered plugin IDs.
        """
        self._plugins.clear()
        if not _PLUGIN_SDK_DIR.exists():
            logger.warning("Plugin SDK directory '%s' not found", _PLUGIN_SDK_DIR)
            return []

        found: List[str] = []
        for entry in _PLUGIN_SDK_DIR.iterdir():
            if not entry.is_dir():
                continue
            manifest = _load_manifest(entry)
            if manifest is None:
                continue
            plugin_id = manifest.get("id", entry.name)
            self._plugins[plugin_id] = {
                "manifest": manifest,
                "dir": entry,
                "module": None,
            }
            found.append(plugin_id)
            logger.info("Discovered plugin '%s' (%s)", plugin_id, entry)

        return found

    async def run_plugin(
        self, plugin_id: str, task: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        """Execute *plugin_id* with *task* under Judge supervision.

        The plugin's entry-point module must expose a callable ``run(task)``
        (sync or async).

        Returns:
            ``(success: bool, result_or_error)``
        """
        if plugin_id not in self._plugins:
            return False, f"Plugin '{plugin_id}' not discovered"

        judge_task = {**task, "resource": f"plugin:{plugin_id}"}
        approved, reason = await self._judge.approve_task(
            self.AGENT_ID, judge_task
        )
        if not approved:
            return False, f"Judge rejected plugin run: {reason}"

        plugin_info = self._plugins[plugin_id]
        try:
            # Lazy-load the module
            if plugin_info["module"] is None:
                manifest = plugin_info["manifest"]
                plugin_info["module"] = _load_plugin_module(
                    plugin_info["dir"], manifest.get("entry", "main.py")
                )
            module = plugin_info["module"]
            if not hasattr(module, "run"):
                raise AttributeError(
                    f"Plugin '{plugin_id}' has no 'run' function"
                )
            result = module.run(task)
            # Support async plugins
            if hasattr(result, "__await__"):
                import asyncio
                result = await result
            logger.info("Plugin '%s' completed successfully", plugin_id)
            return True, result
        except Exception as exc:
            logger.error(
                "Plugin '%s' raised: %s", plugin_id, exc, exc_info=True
            )
            return False, str(exc)
        finally:
            await self._judge.release_task(
                self.AGENT_ID, f"plugin:{plugin_id}"
            )
