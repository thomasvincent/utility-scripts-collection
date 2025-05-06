"""
Configuration management for OpsForge.

This module provides consistent configuration management across
all modules, supporting environment variables, config files,
and command-line arguments.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigManager:
    """Central configuration management for OpsForge.

    This class handles loading configuration from environment variables,
    YAML config files, and provides a unified interface for accessing
    configuration values.

    Attributes:
        config (Dict[str, Any]): The loaded configuration values.
        config_path (Path): Path to the configuration file.
    """

    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        env_prefix: str = "OPSFORGE_",
        load_env: bool = True,
    ):
        """Initialize the ConfigManager.

        Args:
            config_file: Path to a YAML configuration file.
            env_prefix: Prefix for environment variables to load.
            load_env: Whether to load from .env file if present.
        """
        self.config: Dict[str, Any] = {}
        self.config_path: Optional[Path] = None

        # Load environment variables if needed
        if load_env:
            self._load_env_vars()

        # Load environment variables with prefix
        self._load_from_env(env_prefix)

        # Load from config file if provided
        if config_file:
            config_path = Path(config_file)
            if config_path.exists():
                self.config_path = config_path
                self._load_from_file(config_path)
            else:
                logger.warning(f"Config file not found: {config_file}")

    def _load_env_vars(self) -> None:
        """Load environment variables from .env file if it exists."""
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
            logger.debug(f"Loaded environment variables from {env_path}")

    def _load_from_env(self, prefix: str) -> None:
        """Load configuration from environment variables with prefix.

        Args:
            prefix: The prefix for environment variables to load.
        """
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert to nested dict structure
                parts = key[len(prefix) :].lower().split("_")
                current = self.config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
                logger.debug(f"Loaded config from env: {key}")

    def _load_from_file(self, file_path: Path) -> None:
        """Load configuration from a YAML file.

        Args:
            file_path: Path to the YAML configuration file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # Merge with existing config
                    self._merge_configs(self.config, file_config)
                    logger.debug(f"Loaded config from file: {file_path}")
        except Exception as e:
            logger.error(f"Error loading config file {file_path}: {str(e)}")

    def _merge_configs(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
        """Recursively merge two configuration dictionaries.

        Args:
            base: The base configuration dictionary to update.
            overlay: The overlay configuration to merge into base.
        """
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Supports dot notation for nested keys.

        Args:
            key: The configuration key to retrieve.
            default: Default value if key is not found.

        Returns:
            The configuration value if found, otherwise the default.
        """
        parts = key.split(".")
        current = self.config
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Supports dot notation for nested keys.

        Args:
            key: The configuration key to set.
            value: The value to set.
        """
        parts = key.split(".")
        current = self.config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
        logger.debug(f"Set config value: {key}")

    def save(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save the current configuration to a YAML file.

        Args:
            file_path: Path to save the configuration file.
                If None, use the previously loaded config_path.
        """
        if file_path:
            save_path = Path(file_path)
        elif self.config_path:
            save_path = self.config_path
        else:
            logger.error("No file path specified for saving configuration")
            return

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, default_flow_style=False)
                logger.debug(f"Saved config to file: {save_path}")
        except Exception as e:
            logger.error(f"Error saving config file {save_path}: {str(e)}")