"""
Common utilities and shared functions for the opsforge package.

This module provides shared functionality used across the different
modules, including configuration management, logging,
error handling, and other common utilities.
"""

from opsforge.common.config import ConfigManager
from opsforge.common.logging import setup_logging, get_logger
from opsforge.common.exceptions import (
    OpsForgeError,
    ConfigurationError,
    NetworkError,
    ValidationError,
)