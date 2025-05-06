"""
DNS record management tool.

This module provides a comprehensive tool for managing DNS records,
including retrieving zone information, searching for records,
importing from TinyDNS data, and integration with Google Sheets.

Typical usage:
    $ python -m utility_scripts.dns.manager --get example.com

For more options:
    $ python -m utility_scripts.dns.manager --help
"""

import argparse
import contextlib
import getpass
import ipaddress
import os
import pathlib
import re
import secrets
import shlex
import tempfile
import logging
from typing import Dict, List, Optional, Any, Union, Tuple

import dns.resolver
import dns.zone
import dns.query
import dns.name

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

from utility_scripts.common.logging import setup_logging, get_logger
from utility_scripts.common.exceptions import (
    UtilityScriptError,
    ConfigurationError,
    NetworkError,
    AuthenticationError,
    ResourceNotFoundError,
)

# Set up logger
logger = get_logger(__name__)


class DNSError(UtilityScriptError):
    """Error during DNS operations."""
    
    def __init__(self, message: str = "DNS operation failed"):
        super().__init__(f"DNS error: {message}")


class GoogleSheetsError(UtilityScriptError):
    """Error during Google Sheets operations."""
    
    def __init__(self, message: str = "Google Sheets operation failed"):
        super().__init__(f"Google Sheets error: {message}")


class TinyDNSError(UtilityScriptError):
    """Error during TinyDNS operations."""
    
    def __init__(self, message: str = "TinyDNS operation failed"):
        super().__init__(f"TinyDNS error: {message}")


class DNSManager:
    """Manages DNS record operations."""
    
    def __init__(self):
        """Initialize the DNS Manager."""
        self.resolver = dns.resolver.Resolver()
        # Use default configuration from /etc/resolv.conf
    
    def get_zone(self, domain: str, name_server: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves zone records for a domain.
        
        Args:
            domain: The domain to retrieve zone records for.
            name_server: Optional name server to query. If None, uses the system resolver.
            
        Returns:
            Dictionary containing zone information.
            
        Raises:
            DNSError: If retrieving zone information fails.
        """
        try:
            if name_server:
                self.resolver.nameservers = [name_server]
            
            logger.info(f"Retrieving zone information for {domain}")
            
            # Get the SOA record to find the primary name server
            try:
                soa_answers = self.resolver.resolve(domain, 'SOA')
                primary_ns = str(soa_answers[0].mname)
                logger.debug(f"Primary name server for {domain}: {primary_ns}")
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN) as e:
                raise DNSError(f"Could not find SOA record for {domain}: {str(e)}")
            
            # Prepare to store records
            records = {
                "SOA": [{"mname": str(soa_answers[0].mname), 
                         "rname": str(soa_answers[0].rname),
                         "serial": soa_answers[0].serial,
                         "refresh": soa_answers[0].refresh,
                         "retry": soa_answers[0].retry,
                         "expire": soa_answers[0].expire,
                         "minimum": soa_answers[0].minimum}]
            }
            
            # Get NS records
            try:
                ns_answers = self.resolver.resolve(domain, 'NS')
                records["NS"] = [{"nameserver": str(rdata)} for rdata in ns_answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                records["NS"] = []
                logger.warning(f"No NS records found for {domain}")
            
            # Get A records
            try:
                a_answers = self.resolver.resolve(domain, 'A')
                records["A"] = [{"address": str(rdata)} for rdata in a_answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                records["A"] = []
                logger.warning(f"No A records found for {domain}")
            
            # Get MX records
            try:
                mx_answers = self.resolver.resolve(domain, 'MX')
                records["MX"] = [{"preference": rdata.preference, 
                                 "exchange": str(rdata.exchange)} 
                                for rdata in mx_answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                records["MX"] = []
                logger.warning(f"No MX records found for {domain}")
            
            # Get TXT records
            try:
                txt_answers = self.resolver.resolve(domain, 'TXT')
                records["TXT"] = [{"text": str(rdata).strip('"')} for rdata in txt_answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                records["TXT"] = []
                logger.warning(f"No TXT records found for {domain}")
                
            # Zone retrieval summary
            logger.info(f"Retrieved {sum(len(v) for v in records.values())} records for {domain}")
            
            return records
            
        except dns.resolver.NXDOMAIN:
            raise ResourceNotFoundError("Domain", domain)
        except dns.resolver.NoNameservers:
            raise NetworkError(f"No nameservers available for {domain}")
        except dns.exception.DNSException as e:
            raise DNSError(f"DNS error when retrieving zone for {domain}: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error retrieving zone for {domain}")
            raise DNSError(f"Failed to retrieve zone information for {domain}: {str(e)}")
    
    def search_file(self, hostname: str, filename: str) -> List[str]:
        """
        Searches for a hostname within a file.
        
        Args:
            hostname: The hostname to search for.
            filename: The path to the file to search.
            
        Returns:
            List of matching lines.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            PermissionError: If the file cannot be read.
        """
        try:
            logger.info(f"Searching for {hostname} in {filename}")
            matches = []
            
            with pathlib.Path(filename).open('r') as file:
                for line_num, line in enumerate(file, 1):
                    if hostname in line:
                        matches.append(f"{line_num}: {line.strip()}")
            
            logger.info(f"Found {len(matches)} matches for {hostname} in {filename}")
            return matches
            
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
            raise
        except PermissionError:
            logger.error(f"Permission denied to read file: {filename}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error searching file {filename}")
            raise UtilityScriptError(f"Error searching file: {str(e)}")
    
    def import_tinydns(self, directory: Union[str, pathlib.Path]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Imports records from a TinyDNS data directory.
        
        Args:
            directory: Path to the TinyDNS data directory.
            
        Returns:
            Dictionary of imported records by type.
            
        Raises:
            TinyDNSError: If importing TinyDNS data fails.
        """
        try:
            directory = pathlib.Path(directory)
            data_file = directory / "data"
            
            if not directory.exists():
                raise FileNotFoundError(f"TinyDNS directory not found: {directory}")
            
            if not data_file.exists():
                raise FileNotFoundError(f"TinyDNS data file not found: {data_file}")
            
            logger.info(f"Importing TinyDNS data from {data_file}")
            
            records = {
                "A": [],
                "NS": [],
                "MX": [],
                "CNAME": [],
                "TXT": [],
                "SOA": [],
                "PTR": [],
                "Other": []
            }
            
            with data_file.open('r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        record_type = self._parse_tinydns_line(line, records)
                        logger.debug(f"Parsed TinyDNS {record_type} record from line {line_num}")
                    except ValueError as e:
                        logger.warning(f"Error parsing line {line_num}: {str(e)}")
                        # Skip invalid lines
            
            total_records = sum(len(v) for v in records.values())
            logger.info(f"Imported {total_records} records from TinyDNS data")
            
            return records
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            raise
        except PermissionError:
            logger.error(f"Permission denied to read TinyDNS data")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error importing TinyDNS data")
            raise TinyDNSError(f"Error importing TinyDNS data: {str(e)}")
    
    def _parse_tinydns_line(self, line: str, records: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Parse a line from a TinyDNS data file.
        
        Args:
            line: TinyDNS data line.
            records: Dictionary to add parsed records to.
            
        Returns:
            The type of record parsed.
            
        Raises:
            ValueError: If the line cannot be parsed.
        """
        if not line:
            raise ValueError("Empty line")
        
        record_type = line[0]
        
        # Basic parsing of common TinyDNS record types
        try:
            if record_type == '+':  # A record
                parts = line[1:].split(':')
                if len(parts) >= 3:
                    records["A"].append({
                        "hostname": parts[0],
                        "ip": parts[1],
                        "ttl": parts[2] if len(parts) > 2 and parts[2] else "86400"
                    })
                return "A"
                
            elif record_type == '@':  # MX record
                parts = line[1:].split(':')
                if len(parts) >= 4:
                    records["MX"].append({
                        "hostname": parts[0],
                        "ip": parts[1],
                        "priority": parts[2],
                        "ttl": parts[3] if len(parts) > 3 and parts[3] else "86400"
                    })
                return "MX"
                
            elif record_type == 'C':  # CNAME record
                parts = line[1:].split(':')
                if len(parts) >= 2:
                    records["CNAME"].append({
                        "alias": parts[0],
                        "hostname": parts[1],
                        "ttl": parts[2] if len(parts) > 2 and parts[2] else "86400"
                    })
                return "CNAME"
                
            elif record_type == '^':  # PTR record
                parts = line[1:].split(':')
                if len(parts) >= 2:
                    records["PTR"].append({
                        "ip": parts[0],
                        "hostname": parts[1],
                        "ttl": parts[2] if len(parts) > 2 and parts[2] else "86400"
                    })
                return "PTR"
                
            elif record_type == 'Z':  # SOA record
                parts = line[1:].split(':')
                if len(parts) >= 2:
                    records["SOA"].append({
                        "domain": parts[0],
                        "source": parts[1],
                        # Remaining SOA fields would be parsed here
                    })
                return "SOA"
                
            elif record_type == '&':  # NS record
                parts = line[1:].split(':')
                if len(parts) >= 2:
                    records["NS"].append({
                        "domain": parts[0],
                        "ns": parts[1],
                        "ttl": parts[2] if len(parts) > 2 and parts[2] else "86400"
                    })
                return "NS"
                
            else:
                records["Other"].append({"raw_line": line})
                return "Other"
                
        except Exception as e:
            raise ValueError(f"Error parsing TinyDNS line: {str(e)}")


class GoogleSheetsManager:
    """Manages Google Sheets integration."""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize the Google Sheets Manager.
        
        Args:
            credentials_file: Path to Google API credentials JSON file.
            
        Raises:
            GoogleSheetsError: If Google Sheets dependencies are not available.
        """
        if not GOOGLE_SHEETS_AVAILABLE:
            raise GoogleSheetsError(
                "Google Sheets integration requires additional packages. "
                "Install with: pip install gspread oauth2client"
            )
        
        self.credentials_file = credentials_file
        self.client = None
    
    def authenticate(self, credentials_file: Optional[str] = None) -> None:
        """
        Authenticate with Google Sheets API.
        
        Args:
            credentials_file: Path to Google API credentials JSON file.
            
        Raises:
            AuthenticationError: If authentication fails.
            FileNotFoundError: If credentials file is not found.
        """
        creds_file = credentials_file or self.credentials_file
        
        if not creds_file:
            raise ConfigurationError("Google API credentials file is required")
        
        try:
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Authenticate using service account credentials
            credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
            self.client = gspread.authorize(credentials)
            logger.info("Successfully authenticated with Google Sheets API")
            
        except FileNotFoundError:
            logger.error(f"Credentials file not found: {creds_file}")
            raise
        except Exception as e:
            logger.exception(f"Google Sheets authentication failed")
            raise AuthenticationError(f"Google Sheets authentication failed: {str(e)}")
    
    def search_spreadsheet(self, 
                         spreadsheet_key: str, 
                         pattern: str, 
                         case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search for a pattern in a Google Sheets spreadsheet.
        
        Args:
            spreadsheet_key: The unique identifier for the spreadsheet.
            pattern: The pattern to search for.
            case_sensitive: Whether the search should be case-sensitive.
            
        Returns:
            List of dictionaries containing matched cells.
            
        Raises:
            GoogleSheetsError: If spreadsheet operations fail.
            AuthenticationError: If not authenticated.
        """
        if not self.client:
            raise AuthenticationError("Not authenticated with Google Sheets API")
        
        try:
            logger.info(f"Searching for '{pattern}' in spreadsheet {spreadsheet_key}")
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(spreadsheet_key)
            
            # Prepare results
            results = []
            
            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            
            # Search all worksheets
            for worksheet in spreadsheet.worksheets():
                logger.debug(f"Searching worksheet: {worksheet.title}")
                
                # Get all values
                values = worksheet.get_all_values()
                
                # Search each cell
                for row_idx, row in enumerate(values, 1):
                    for col_idx, cell in enumerate(row, 1):
                        if regex.search(cell):
                            results.append({
                                "sheet": worksheet.title,
                                "row": row_idx,
                                "column": col_idx,
                                "value": cell,
                                "a1_notation": f"{worksheet.title}!{gspread.utils.rowcol_to_a1(row_idx, col_idx)}"
                            })
            
            logger.info(f"Found {len(results)} matches for '{pattern}'")
            return results
            
        except gspread.exceptions.SpreadsheetNotFound:
            raise ResourceNotFoundError("Spreadsheet", spreadsheet_key)
        except gspread.exceptions.APIError as e:
            raise GoogleSheetsError(f"Google Sheets API error: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error searching Google Sheets")
            raise GoogleSheetsError(f"Error searching spreadsheet: {str(e)}")


def main() -> None:
    """Parse arguments and execute the requested operation."""
    # Set up logging
    setup_logging()
    
    parser = argparse.ArgumentParser(description="DNS record management tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Get zone records command
    get_parser = subparsers.add_parser("get", help="Get zone records for a domain")
    get_parser.add_argument("domain", help="Domain to retrieve zone records for")
    get_parser.add_argument("--server", "-s", help="Name server to query")
    
    # Search file command
    search_parser = subparsers.add_parser("search", help="Search for a hostname in a file")
    search_parser.add_argument("hostname", help="Hostname to search for")
    search_parser.add_argument("--file", "-f", required=True, help="File to search in")
    
    # Import TinyDNS command
    tinydns_parser = subparsers.add_parser("tinydns", help="Import records from TinyDNS data directory")
    tinydns_parser.add_argument("--directory", "-d", 
                               default="/service/tinydns", 
                               help="TinyDNS data directory (default: /service/tinydns)")
    
    # Google Sheets search command
    if GOOGLE_SHEETS_AVAILABLE:
        gdocs_parser = subparsers.add_parser("sheets", help="Search for a pattern in a Google Sheets spreadsheet")
        gdocs_parser.add_argument("pattern", help="Pattern to search for")
        gdocs_parser.add_argument("--key", "-k", required=True, help="Spreadsheet key/ID")
        gdocs_parser.add_argument("--credentials", "-c", required=True, help="Google API credentials JSON file")
        gdocs_parser.add_argument("--case-sensitive", action="store_true", help="Enable case-sensitive search")
    
    args = parser.parse_args()
    
    try:
        if args.command == "get":
            dns_manager = DNSManager()
            records = dns_manager.get_zone(args.domain, args.server)
            
            # Print results in a readable format
            print(f"\nZone information for {args.domain}:\n")
            
            # SOA Records
            if records["SOA"]:
                print("SOA Records:")
                for soa in records["SOA"]:
                    print(f"  Primary NS: {soa['mname']}")
                    print(f"  Admin: {soa['rname']}")
                    print(f"  Serial: {soa['serial']}")
                    print(f"  Refresh: {soa['refresh']}")
                    print(f"  Retry: {soa['retry']}")
                    print(f"  Expire: {soa['expire']}")
                    print(f"  Minimum TTL: {soa['minimum']}")
                print()
            
            # NS Records
            if records["NS"]:
                print("NS Records:")
                for ns in records["NS"]:
                    print(f"  {ns['nameserver']}")
                print()
            
            # A Records
            if records["A"]:
                print("A Records:")
                for a in records["A"]:
                    print(f"  {args.domain} -> {a['address']}")
                print()
            
            # MX Records
            if records["MX"]:
                print("MX Records:")
                for mx in records["MX"]:
                    print(f"  {mx['preference']} {mx['exchange']}")
                print()
            
            # TXT Records
            if records["TXT"]:
                print("TXT Records:")
                for txt in records["TXT"]:
                    print(f"  {txt['text']}")
                print()
            
        elif args.command == "search":
            dns_manager = DNSManager()
            matches = dns_manager.search_file(args.hostname, args.file)
            
            if matches:
                print(f"\nMatches for '{args.hostname}' in {args.file}:\n")
                for match in matches:
                    print(match)
            else:
                print(f"\nNo matches found for '{args.hostname}' in {args.file}\n")
            
        elif args.command == "tinydns":
            dns_manager = DNSManager()
            records = dns_manager.import_tinydns(args.directory)
            
            # Print a summary of imported records
            print(f"\nImported records from TinyDNS data in {args.directory}:\n")
            for record_type, entries in records.items():
                if entries:
                    print(f"{record_type} Records: {len(entries)}")
            
            # Print some sample records
            for record_type, entries in records.items():
                if entries and record_type != "Other":
                    print(f"\nSample {record_type} Records:")
                    for i, entry in enumerate(entries[:5]):
                        if record_type == "A":
                            print(f"  {entry['hostname']} -> {entry['ip']}")
                        elif record_type == "MX":
                            print(f"  {entry['hostname']} -> {entry['priority']} {entry['ip']}")
                        elif record_type == "CNAME":
                            print(f"  {entry['alias']} -> {entry['hostname']}")
                        elif record_type == "NS":
                            print(f"  {entry['domain']} -> {entry['ns']}")
                        # Add other record types as needed
                    
                    if len(entries) > 5:
                        print(f"  ... and {len(entries) - 5} more")
            
        elif args.command == "sheets" and GOOGLE_SHEETS_AVAILABLE:
            sheets_manager = GoogleSheetsManager()
            sheets_manager.authenticate(args.credentials)
            results = sheets_manager.search_spreadsheet(
                args.key, args.pattern, args.case_sensitive
            )
            
            if results:
                print(f"\nMatches for '{args.pattern}' in spreadsheet:\n")
                for result in results:
                    print(f"Sheet: {result['sheet']}, Cell: {result['a1_notation']}, Value: {result['value']}")
            else:
                print(f"\nNo matches found for '{args.pattern}' in spreadsheet\n")
            
        else:
            parser.print_help()
            
    except UtilityScriptError as e:
        logger.error(str(e))
        print(f"Error: {str(e)}")
        return 1
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        print("\nOperation interrupted")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error")
        print(f"Unexpected error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    main()