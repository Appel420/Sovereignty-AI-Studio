"""
Configuration fixer for invalid or missing configuration.

Automatically detects and fixes:
  - Missing configuration files
  - Invalid configuration values
  - Missing environment variables
  - Configuration schema violations
"""

import logging
import os
import pathlib
from typing import Any, Optional

from errors.exceptions import ConfigurationError

log = logging.getLogger("fixers.config")


class ConfigFixer:
    """
    Validates and repairs configuration issues automatically.
    """

    def __init__(self, defaults: Optional[dict[str, Any]] = None):
        self.defaults = defaults or self._get_default_config()
        self._fixed_keys: set[str] = set()

    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        """Get default configuration values."""
        return {
            "SG_PORT": 9897,
            "SG_HOST": "localhost",
            "NODE_BRIDGE_PORT": 9899,
            "FRONTEND_PORT": 9898,
            "SOVEREIGN_API_URL": "http://localhost:9899/api/ai",
            "LOG_LEVEL": "INFO",
            "MAX_CLIENTS": 100,
            "PING_INTERVAL": 20,
            "PING_TIMEOUT": 30,
            "MAX_MESSAGE_SIZE": 50 * 1024 * 1024,  # 50MB
        }

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate configuration values.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, list of issues found)
        """
        issues = []

        # Check ports
        for key, value in config.items():
            if key.endswith("_PORT"):
                if not isinstance(value, int) or value < 1 or value > 65535:
                    issues.append(f"Invalid port for {key}: {value}")

        # Check host
        if "SG_HOST" in config:
            host = config["SG_HOST"]
            if not isinstance(host, str) or not host:
                issues.append(f"Invalid host: {host}")

        # Check URLs
        if "SOVEREIGN_API_URL" in config:
            url = config["SOVEREIGN_API_URL"]
            if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
                issues.append(f"Invalid API URL: {url}")

        # Check numeric values
        numeric_keys = {
            "MAX_CLIENTS": (1, 10000),
            "PING_INTERVAL": (1, 300),
            "PING_TIMEOUT": (1, 600),
            "MAX_MESSAGE_SIZE": (1024, 1024 * 1024 * 1024),  # 1KB to 1GB
        }

        for key, (min_val, max_val) in numeric_keys.items():
            if key in config:
                value = config[key]
                if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                    issues.append(f"Invalid {key}: {value} (must be between {min_val} and {max_val})")

        is_valid = len(issues) == 0
        return is_valid, issues

    def fix_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Fix configuration by applying defaults for missing or invalid values.

        Args:
            config: Configuration dictionary to fix

        Returns:
            Fixed configuration dictionary
        """
        fixed = config.copy()
        is_valid, issues = self.validate_config(fixed)

        if is_valid:
            log.info("Configuration is valid")
            return fixed

        log.warning("Configuration issues detected: %s", issues)

        # Apply defaults for invalid values
        for key, default_value in self.defaults.items():
            if key not in fixed or self._is_invalid_value(fixed, key):
                log.info("Fixing config key '%s' with default: %s", key, default_value)
                fixed[key] = default_value
                self._fixed_keys.add(key)

        # Validate again
        is_valid, remaining_issues = self.validate_config(fixed)
        if not is_valid:
            log.warning("Some configuration issues remain: %s", remaining_issues)

        return fixed

    def _is_invalid_value(self, config: dict, key: str) -> bool:
        """Check if a specific config value is invalid."""
        is_valid, issues = self.validate_config({key: config[key]})
        return not is_valid

    def fix_env_config(self) -> dict[str, Any]:
        """
        Fix configuration from environment variables.

        Returns:
            Fixed configuration dictionary
        """
        config = {}

        # Load from environment
        for key in self.defaults:
            value = os.environ.get(key)
            if value is not None:
                # Try to convert to appropriate type
                if key.endswith("_PORT") or key.startswith("MAX_") or key.endswith("_INTERVAL") or key.endswith("_TIMEOUT"):
                    try:
                        config[key] = int(value)
                    except ValueError:
                        log.warning("Invalid integer value for %s: %s", key, value)
                else:
                    config[key] = value

        return self.fix_config(config)

    def ensure_config_file(self, config_path: pathlib.Path) -> bool:
        """
        Ensure configuration file exists with valid content.

        Args:
            config_path: Path to configuration file

        Returns:
            True if config file is valid or was fixed
        """
        import json

        # Create if missing
        if not config_path.exists():
            log.info("Creating missing configuration file: %s", config_path)
            try:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(self.defaults, f, indent=2)
                return True
            except Exception as e:
                log.error("Failed to create configuration file: %s", e)
                return False

        # Validate existing file
        try:
            with open(config_path) as f:
                config = json.load(f)

            is_valid, issues = self.validate_config(config)

            if not is_valid:
                log.warning("Configuration file has issues: %s", issues)
                fixed_config = self.fix_config(config)

                # Write fixed config
                with open(config_path, "w") as f:
                    json.dump(fixed_config, f, indent=2)
                log.info("Configuration file fixed: %s", config_path)

            return True

        except Exception as e:
            log.error("Failed to process configuration file: %s", e)
            return False

    def status(self) -> dict:
        """Get current configuration fixer status."""
        return {
            "defaults": self.defaults,
            "fixed_keys": list(self._fixed_keys),
            "fixed_count": len(self._fixed_keys),
        }
