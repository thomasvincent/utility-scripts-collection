"""Command-line interface for OpsForge.

This module provides the main CLI entry point for the OpsForge package,
integrating all commands under a single interface.
"""

import argparse
import importlib
import sys
from typing import Any, Dict, List, Optional

from opsforge.common.exceptions import OpsForgeError
from opsforge.common.logging import setup_logging


def main() -> int:
    """Main entry point for the OpsForge CLI.
    
    Returns:
        int: Exit code (0 for success, non-zero for errors).
    """
    # Set up logging
    setup_logging()
    
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        prog="opsforge",
        description="OpsForge: Essential tools for DevOps engineers and system administrators.",
    )
    
    # Create a subparser for each command
    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute")
    
    # HTTP commands
    http500_parser = subparsers.add_parser(
        "http500", help="Monitor HTTP 500 errors")
    http500_parser.add_argument(
        "--host", required=True, help="Host to check")
    http500_parser.add_argument(
        "--email", required=True, help="Email for notifications")
    http500_parser.add_argument(
        "--port", type=int, help="Port number")
    http500_parser.add_argument(
        "--scheme", choices=["http", "https"], help="Protocol scheme")
    http500_parser.add_argument(
        "--path", default="/", help="Path to check")
    http500_parser.add_argument(
        "--codes", type=int, nargs="+", help="HTTP status codes to alert on")
    http500_parser.add_argument(
        "--timeout", type=int, help="Request timeout in seconds")
    
    # Filesystem commands
    readonly_parser = subparsers.add_parser(
        "readonly", help="Check for read-only filesystems")
    readonly_parser.add_argument(
        "--host", "-H", required=True, help="SSH Remote host")
    readonly_parser.add_argument(
        "--user", "-u", default="root", help="SSH Remote user")
    readonly_parser.add_argument(
        "--port", "-p", type=int, default=22, help="SSH Remote port")
    readonly_parser.add_argument(
        "--identity", "-i", help="SSH identity file")
    readonly_parser.add_argument(
        "--mount-table", "-m", default="/proc/mounts", help="Mount table path")
    readonly_parser.add_argument(
        "--partition", "-P", action="append", dest="part_filter",
        help="Pattern of partition to check")
    readonly_parser.add_argument(
        "--exclude", "-x", dest="exclude", help="Pattern of partition to ignore")
    readonly_parser.add_argument(
        "--exclude-type", "-X", action="append", dest="exclude_type",
        help="File system types to exclude")
    
    # DNS commands
    dns_parser = subparsers.add_parser(
        "dns", help="DNS management tools")
    dns_subparsers = dns_parser.add_subparsers(dest="dns_command")
    
    # DNS get
    dns_get_parser = dns_subparsers.add_parser(
        "get", help="Get zone records for a domain")
    dns_get_parser.add_argument(
        "domain", help="Domain to retrieve zone records for")
    dns_get_parser.add_argument(
        "--server", "-s", help="Name server to query")
    
    # DNS search
    dns_search_parser = dns_subparsers.add_parser(
        "search", help="Search for a hostname in a file")
    dns_search_parser.add_argument(
        "hostname", help="Hostname to search for")
    dns_search_parser.add_argument(
        "--file", "-f", required=True, help="File to search in")
    
    # DNS tinydns
    dns_tinydns_parser = dns_subparsers.add_parser(
        "tinydns", help="Import records from TinyDNS data directory")
    dns_tinydns_parser.add_argument(
        "--directory", "-d", default="/service/tinydns",
        help="TinyDNS data directory")
    
    # Parse the arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        # Execute the appropriate command
        if args.command == "http500":
            # Import and call the http500 module's main function
            from opsforge.http.http500 import main as http500_main
            return http500_main() or 0
            
        elif args.command == "readonly":
            # Import and call the readonly module's main function
            from opsforge.filesystem.readonly import main as readonly_main
            return readonly_main() or 0
            
        elif args.command == "dns":
            # Handle DNS commands
            if not args.dns_command:
                dns_parser.print_help()
                return 0
                
            # Import and call the dns module's main function
            from opsforge.dns.manager import main as dns_main
            return dns_main() or 0
            
        else:
            parser.print_help()
            return 0
            
    except OpsForgeError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())