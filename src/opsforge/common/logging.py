"""
Logging utilities for OpsForge.

This module provides consistent logging configuration across all
OpsForge modules, with support for various log destinations and formats.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Union


def setup_logging(
    log_level: Union[int, str] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    log_format: Optional[str] = None,
    module_levels: Optional[Dict[str, Union[int, str]]] = None,
) -> None:
    """Configure logging for OpsForge.

    Args:
        log_level: The log level to use (default: INFO).
        log_file: Optional file path to write logs to.
        log_format: Optional custom log format. If None, a default format is used.
        module_levels: Optional dictionary mapping module names to specific log levels.
    """
    # Convert string log levels to constants if needed
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper())

    # Default log format
    if not log_format:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Always add a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add a file handler if requested
    if log_file:
        file_path = Path(log_file)
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific levels for modules if provided
    if module_levels:
        for module_name, level in module_levels.items():
            if isinstance(level, str):
                level = getattr(logging, level.upper())
            logging.getLogger(module_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: The name of the logger, typically __name__.

    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)