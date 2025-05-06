"""
Custom exceptions for the OpsForge package.

This module defines a consistent set of exceptions used across
all OpsForge modules, allowing for more specific error handling.
"""


class OpsForgeError(Exception):
    """Base exception for all OpsForge errors."""

    def __init__(self, message: str = "An error occurred in OpsForge"):
        self.message = message
        super().__init__(self.message)


class ConfigurationError(OpsForgeError):
    """Exception raised for errors in the configuration."""

    def __init__(self, message: str = "Configuration error"):
        super().__init__(f"Configuration error: {message}")


class NetworkError(OpsForgeError):
    """Exception raised for network-related errors."""

    def __init__(self, message: str = "Network error"):
        super().__init__(f"Network error: {message}")


class ValidationError(OpsForgeError):
    """Exception raised for validation errors."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(f"Validation error: {message}")


class AuthenticationError(OpsForgeError):
    """Exception raised for authentication failures."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(f"Authentication error: {message}")


class DataProcessingError(OpsForgeError):
    """Exception raised for data processing errors."""

    def __init__(self, message: str = "Data processing failed"):
        super().__init__(f"Data processing error: {message}")


class ResourceNotFoundError(OpsForgeError):
    """Exception raised when a requested resource is not found."""

    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} not found: {identifier}"
        super().__init__(message)