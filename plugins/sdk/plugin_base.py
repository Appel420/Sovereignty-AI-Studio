"""
Plugin SDK — base class for all Sovereignty AI Studio plugins.

Every plugin must subclass PluginBase and implement:
  - run(payload: dict) -> Any
  - configure(config: dict) -> None
  - health_check() -> bool

Optionally override:
  - start() — called when plugin is activated
  - stop() — called when plugin is deactivated
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging


class PluginBase(ABC):
    """
    Abstract base class for Sovereignty AI Studio plugins.

    Subclass this to build a custom agent or tool plugin.
    Register via the marketplace API or place in plugins/examples.
    """

    # Override in subclass
    name: str = "unnamed_plugin"
    display_name: str = "Unnamed Plugin"
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    category: str = "general"

    def __init__(self, config: Optional[Dict] = None):
        self.config: Dict = config or {}
        self.logger = logging.getLogger(f"plugin.{self.name}")
        self._active = False

    # ── Required interface ─────────────────────────────────────────────────────

    @abstractmethod
    def run(self, payload: Dict) -> Any:
        """
        Execute the plugin's primary action.

        Args:
            payload: Input data for this execution.

        Returns:
            Any: Plugin-specific output.
        """

    @abstractmethod
    def configure(self, config: Dict) -> None:
        """
        Apply runtime configuration.

        Args:
            config: Key-value configuration dictionary.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verify the plugin is healthy and ready to serve requests.

        Returns:
            bool: True if healthy, False otherwise.
        """

    # ── Optional lifecycle hooks ───────────────────────────────────────────────

    def start(self) -> None:
        """Called once when the plugin is activated. Override to initialize resources."""
        self._active = True
        self.logger.info("Plugin '%s' v%s started", self.name, self.version)

    def stop(self) -> None:
        """Called once when the plugin is deactivated. Override to release resources."""
        self._active = False
        self.logger.info("Plugin '%s' stopped", self.name)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._active

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def metadata(self) -> Dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category,
            "active": self._active,
        }
