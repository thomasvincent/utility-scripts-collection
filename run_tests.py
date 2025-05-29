#!/usr/bin/env python3
"""Test runner script for the utility-scripts-collection project.

This script runs all tests, linting, and type checking for the project.
It follows Google Python Style Guide conventions.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """Run a command and return success status and output.
    
    Args:
        cmd: Command to run as list of strings
        description: Description of what the command does
        
    Returns:
        Tuple of (success, output)
    """
    print(f"\n{BLUE}Running: {description}{RESET}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"{GREEN}✓ {description} passed{RESET}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"{RED}✗ {description} failed{RESET}")
        print(f"Error output:\n{e.stderr}")
        return False, e.stderr
    except FileNotFoundError:
        print(f"{YELLOW}⚠ {cmd[0]} not found - skipping{RESET}")
        return True, "Tool not found"


def main():
    """Run all tests and checks."""
    print(f"{BLUE}=== Utility Scripts Collection - Test Runner ==={RESET}")
    
    # Change to project root
    project_root = Path(__file__).parent
    
    all_passed = True
    
    # 1. Run pytest with coverage
    passed, _ = run_command(
        ["pytest", "-v", "--cov=.", "--cov-report=term-missing"],
        "Running tests with coverage"
    )
    all_passed &= passed
    
    # 2. Run black formatter check
    passed, _ = run_command(
        ["black", "--check", "--diff", "."],
        "Checking code formatting with Black"
    )
    all_passed &= passed
    
    # 3. Run isort import check
    passed, _ = run_command(
        ["isort", "--check-only", "--diff", "."],
        "Checking import sorting with isort"
    )
    all_passed &= passed
    
    # 4. Run flake8 linting
    passed, _ = run_command(
        ["flake8", "."],
        "Running flake8 linter"
    )
    all_passed &= passed
    
    # 5. Run pylint
    passed, _ = run_command(
        ["pylint", "src/", "DNSScript/dns_manager.py", 
         "WhoisScript/main.py", "NagiosPlugins/check_http500/check_http500_clean.py"],
        "Running pylint"
    )
    all_passed &= passed
    
    # 6. Run mypy type checking
    passed, _ = run_command(
        ["mypy", "src/", "DNSScript/dns_manager.py", 
         "WhoisScript/main.py", "NagiosPlugins/check_http500/check_http500_clean.py"],
        "Running mypy type checker"
    )
    all_passed &= passed
    
    # 7. Run bandit security check
    passed, _ = run_command(
        ["bandit", "-r", "src/", "DNSScript/", "WhoisScript/", 
         "NagiosPlugins/", "-ll", "--skip", "B101,B601"],
        "Running bandit security scanner"
    )
    all_passed &= passed
    
    # Summary
    print(f"\n{BLUE}=== Test Summary ==={RESET}")
    if all_passed:
        print(f"{GREEN}✓ All tests and checks passed!{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}✗ Some tests or checks failed{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()