#!/usr/bin/env python3
"""
Setup script for the opsforge package.

OpsForge provides a set of essential tools for DevOps engineers and system
administrators, including modules for HTTP monitoring, DNS management,
filesystem checks, and more.
"""

from setuptools import setup, find_packages

# This is a legacy setup.py file for backwards compatibility.
# The actual metadata is stored in pyproject.toml

setup(
    name="opsforge",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
)