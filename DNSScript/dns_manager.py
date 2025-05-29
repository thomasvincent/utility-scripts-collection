#!/usr/bin/env python3
"""DNS record management tool with support for various DNS sources."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import re

import dns.resolver
import dns.zone
from dns.exception import DNSException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DNSRecord:
    """Represents a DNS record."""
    name: str
    record_type: str
    value: str
    ttl: Optional[int] = None
    
    def __str__(self) -> str:
        """Format DNS record for display."""
        ttl_str = f" (TTL: {self.ttl})" if self.ttl else ""
        return f"{self.name} {self.record_type} {self.value}{ttl_str}"


class DNSManager:
    """Manages DNS record operations from various sources."""
    
    def __init__(self):
        """Initialize DNS manager."""
        self.resolver = dns.resolver.Resolver()
    
    def get_zone_records(self, domain: str) -> List[DNSRecord]:
        """
        Retrieve DNS records for a domain.
        
        Args:
            domain: The domain name to query
            
        Returns:
            List of DNS records
            
        Raises:
            DNSException: If DNS query fails
        """
        records = []
        record_types = ['A', 'AAAA', 'MX', 'TXT', 'NS', 'CNAME', 'SOA']
        
        for record_type in record_types:
            try:
                answers = self.resolver.resolve(domain, record_type)
                for rdata in answers:
                    record = DNSRecord(
                        name=domain,
                        record_type=record_type,
                        value=str(rdata),
                        ttl=answers.ttl
                    )
                    records.append(record)
                    logger.debug(f"Found {record_type} record: {record}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                logger.debug(f"No {record_type} records found for {domain}")
            except DNSException as e:
                logger.error(f"DNS error querying {record_type} for {domain}: {e}")
                
        return records
    
    def search_hosts_file(self, hostname: str, filepath: Path) -> List[str]:
        """
        Search for hostname in a hosts file.
        
        Args:
            hostname: Hostname to search for
            filepath: Path to the hosts file
            
        Returns:
            List of matching lines
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file can't be read
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
            
        matches = []
        pattern = re.compile(rf'\b{re.escape(hostname)}\b', re.IGNORECASE)
        
        try:
            with filepath.open('r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip comments and empty lines
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    if pattern.search(line):
                        matches.append(f"{line_num}: {line}")
                        logger.debug(f"Found match on line {line_num}: {line}")
                        
        except PermissionError:
            logger.error(f"Permission denied reading file: {filepath}")
            raise
            
        return matches
    
    def import_tinydns_records(self, data_dir: Path) -> List[DNSRecord]:
        """
        Import DNS records from TinyDNS data files.
        
        Args:
            data_dir: Path to TinyDNS data directory
            
        Returns:
            List of DNS records
            
        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If data format is invalid
        """
        if not data_dir.exists():
            raise FileNotFoundError(f"Directory not found: {data_dir}")
            
        if not data_dir.is_dir():
            raise ValueError(f"Not a directory: {data_dir}")
            
        records = []
        data_file = data_dir / "data"
        
        if not data_file.exists():
            raise FileNotFoundError(f"TinyDNS data file not found: {data_file}")
            
        try:
            with data_file.open('r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    try:
                        record = self._parse_tinydns_line(line)
                        if record:
                            records.append(record)
                    except ValueError as e:
                        logger.warning(f"Invalid TinyDNS record on line {line_num}: {e}")
                        
        except PermissionError:
            logger.error(f"Permission denied reading file: {data_file}")
            raise
            
        return records
    
    def _parse_tinydns_line(self, line: str) -> Optional[DNSRecord]:
        """
        Parse a single TinyDNS data line.
        
        Args:
            line: TinyDNS format line
            
        Returns:
            DNSRecord or None if not parseable
        """
        # TinyDNS format examples:
        # +fqdn:ip:ttl (A record)
        # =fqdn:ip:ttl (A + PTR record)
        # @fqdn:mx:priority:ttl (MX record)
        # 'fqdn:text:ttl (TXT record)
        
        if not line:
            return None
            
        record_type_map = {
            '+': 'A',
            '=': 'A',
            '@': 'MX',
            "'": 'TXT',
            '^': 'PTR',
            'C': 'CNAME'
        }
        
        record_char = line[0]
        if record_char not in record_type_map:
            return None
            
        parts = line[1:].split(':')
        if len(parts) < 2:
            raise ValueError(f"Invalid format: {line}")
            
        fqdn = parts[0]
        value = parts[1]
        ttl = int(parts[-1]) if parts[-1].isdigit() else None
        
        return DNSRecord(
            name=fqdn,
            record_type=record_type_map[record_char],
            value=value,
            ttl=ttl
        )


def main():
    """Main entry point for DNS management tool."""
    parser = argparse.ArgumentParser(
        description="DNS record management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --get example.com
  %(prog)s --search host.example.com --file /etc/hosts
  %(prog)s --tinydns /service/tinydns
        """
    )
    
    parser.add_argument(
        "-g", "--get",
        type=str,
        metavar="DOMAIN",
        help="Get DNS records for a domain"
    )
    
    search_group = parser.add_argument_group("File Search")
    search_group.add_argument(
        "-s", "--search",
        type=str,
        metavar="HOSTNAME",
        help="Search for hostname in a file"
    )
    search_group.add_argument(
        "-f", "--file",
        type=Path,
        metavar="PATH",
        help="Path to the file to search"
    )
    
    parser.add_argument(
        "-t", "--tinydns",
        type=Path,
        metavar="DIR",
        help="Import records from TinyDNS data directory"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    # Initialize DNS manager
    dns_manager = DNSManager()
    
    try:
        if args.get:
            logger.info(f"Querying DNS records for {args.get}")
            records = dns_manager.get_zone_records(args.get)
            
            if records:
                print(f"\nDNS records for {args.get}:")
                for record in records:
                    print(f"  {record}")
            else:
                print(f"No DNS records found for {args.get}")
                
        elif args.search:
            if not args.file:
                parser.error("--search requires --file option")
                
            logger.info(f"Searching for {args.search} in {args.file}")
            matches = dns_manager.search_hosts_file(args.search, args.file)
            
            if matches:
                print(f"\nFound {len(matches)} match(es) for '{args.search}':")
                for match in matches:
                    print(f"  {match}")
            else:
                print(f"No matches found for '{args.search}'")
                
        elif args.tinydns:
            logger.info(f"Importing TinyDNS records from {args.tinydns}")
            records = dns_manager.import_tinydns_records(args.tinydns)
            
            if records:
                print(f"\nImported {len(records)} DNS record(s):")
                for record in records:
                    print(f"  {record}")
            else:
                print("No records found in TinyDNS data")
                
        else:
            parser.print_help()
            
    except (FileNotFoundError, PermissionError, ValueError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()