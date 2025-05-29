#!/usr/bin/env python3

import socket
import argparse
import logging
import sys
from typing import List, Optional
from contextlib import closing
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# --- Constants ---
DEFAULT_WHOIS_PORT: int = 43
DEFAULT_WHOIS_SERVER: str = "whois.internic.net"
DEFAULT_BUFFER_SIZE: int = 4096 # Increased buffer size
DEFAULT_SOCKET_TIMEOUT: float = 10.0 # seconds, use float for settimeout
LINE_ENDING: bytes = b'\r\n'
DEFAULT_INPUT_FILENAME: str = "domains.txt"

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Custom Exceptions ---

class DomainReadError(Exception):
    """Error reading domains from the source."""
    pass

class WhoisLookupError(Exception):
    """Error performing the WHOIS lookup."""
    pass

# --- Domain / Value Objects ---

@dataclass(frozen=True)
class WhoisServerConfig:
    """Configuration for the target WHOIS server."""
    host: str
    port: int

@dataclass(frozen=True)
class WhoisResult:
    """Holds the result of a WHOIS lookup."""
    domain: str
    success: bool
    response: Optional[str] = None
    error_message: Optional[str] = None

# --- Interfaces (Abstract Base Classes) ---

class DomainReader(ABC):
    """Interface for reading domain names from a source."""

    @abstractmethod
    def read_domains(self) -> List[str]:
        """Reads and returns a list of domain names."""
        pass

class WhoisLookup(ABC):
    """Interface for performing WHOIS lookups."""

    @abstractmethod
    def lookup(self, domain: str) -> WhoisResult:
        """Performs a WHOIS lookup for the given domain."""
        pass

# --- Service Implementations ---

class DomainFileReader(DomainReader):
    """Reads domain names from a text file."""

    def __init__(self, filepath: str):
        self._filepath = filepath
        if not filepath:
             raise ValueError("Filepath cannot be empty for DomainFileReader.")
        logger.info(f"Initialized domain reader for file: {self._filepath}")


    def read_domains(self) -> List[str]:
        """
        Reads domains from the configured file, one per line.

        Raises:
            DomainReadError: If the file cannot be read.
        Returns:
            A list of valid domain strings.
        """
        logger.info(f"Attempting to read domains from {self._filepath}")
        try:
            with open(self._filepath, "r", encoding='utf-8') as f:
                # Read lines, strip whitespace, filter out empty lines
                domains = [line.strip() for line in f if line.strip()]
            logger.info(f"Successfully read {len(domains)} domains.")
            return domains
        except FileNotFoundError:
            logger.error(f"Input file not found: {self._filepath}")
            raise DomainReadError(f"Input file not found: {self._filepath}") from None
        except IOError as e:
            logger.error(f"Error reading file {self._filepath}: {e}")
            raise DomainReadError(f"Error reading file {self._filepath}: {e}") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred reading {self._filepath}")
            raise DomainReadError(f"Unexpected error reading file: {e}") from e


class WhoisClient(WhoisLookup):
    """Performs WHOIS lookups using raw socket communication."""

    def __init__(self, server_config: WhoisServerConfig, timeout: float = DEFAULT_SOCKET_TIMEOUT):
        if not server_config:
            raise ValueError("WhoisServerConfig cannot be None for WhoisClient.")
        self._server_config = server_config
        self._timeout = timeout
        logger.info(
            f"Initialized WHOIS client for {server_config.host}:{server_config.port} "
            f"with timeout {timeout}s"
        )


    def lookup(self, domain: str) -> WhoisResult:
        """
        Connects to the WHOIS server and performs the lookup for a domain.

        Returns:
            WhoisResult containing the outcome.
        """
        if not domain:
            return WhoisResult(domain=domain, success=False, error_message="Domain name cannot be empty")

        logger.info(f"Performing WHOIS lookup for '{domain}' via {self._server_config.host}")
        query = f"{domain}{LINE_ENDING.decode()}".encode('idna') # Use IDNA encoding for international domains

        # Use closing for automatic socket closure even with errors
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            try:
                s.settimeout(self._timeout) # Set explicit timeout
                s.connect((self._server_config.host, self._server_config.port))
                s.sendall(query)

                response_bytes = b""
                while True:
                    chunk = s.recv(DEFAULT_BUFFER_SIZE)
                    if not chunk:
                        break
                    response_bytes += chunk

                response_text = response_bytes.decode('utf-8', errors='replace') # Decode safely
                logger.info(f"Successfully received WHOIS response for '{domain}'.")
                return WhoisResult(domain=domain, success=True, response=response_text.strip())

            except socket.timeout:
                error_msg = f"Timeout after {self._timeout}s connecting/reading from {self._server_config.host}:{self._server_config.port}"
                logger.error(f"{error_msg} for domain '{domain}'")
                return WhoisResult(domain=domain, success=False, error_message=error_msg)
            except socket.gaierror as e: # Get address info error (DNS lookup failure)
                 error_msg = f"DNS lookup failed for WHOIS server {self._server_config.host}: {e}"
                 logger.error(f"{error_msg} for domain '{domain}'")
                 return WhoisResult(domain=domain, success=False, error_message=error_msg)
            except socket.error as e: # Other socket errors (connection refused, network unreachable etc)
                error_msg = f"Socket error connecting to {self._server_config.host}:{self._server_config.port}: {e}"
                logger.error(f"{error_msg} for domain '{domain}'")
                return WhoisResult(domain=domain, success=False, error_message=error_msg)
            except Exception as e:
                # Catch any other unexpected errors during the lookup process
                error_msg = f"Unexpected error during WHOIS lookup for {domain}: {e}"
                logger.exception(error_msg) # Log full traceback for unexpected errors
                return WhoisResult(domain=domain, success=False, error_message=error_msg)

# --- Application Service ---

class WhoisApp:
    """Orchestrates reading domains and performing WHOIS lookups."""

    def __init__(self, domain_reader: DomainReader, whois_lookup: WhoisLookup):
        if not domain_reader or not whois_lookup:
             raise ValueError("DomainReader and WhoisLookup must be provided.")
        self._domain_reader = domain_reader
        self._whois_lookup = whois_lookup
        logger.info("WHOIS Application initialized.")

    def run(self) -> None:
        """Executes the main application logic."""
        logger.info("Starting WHOIS application run.")
        try:
            domains = self._domain_reader.read_domains()
        except DomainReadError as e:
            logger.error(f"Failed to start application: {e}")
            print(f"Error: Could not read domains - {e}", file=sys.stderr) # Also print to stderr
            return # Stop execution if domains cannot be read

        if not domains:
            logger.warning("No domains found to process.")
            print("Warning: No domains found in the input source.")
            return

        logger.info(f"Processing {len(domains)} domains...")
        successful_lookups = 0
        failed_lookups = 0

        for domain in domains:
            result = self._whois_lookup.lookup(domain)
            print("-" * 40) # Separator for readability
            if result.success:
                print(f"WHOIS lookup successful for: {domain}")
                print(result.response)
                successful_lookups += 1
            else:
                print(f"WHOIS lookup FAILED for: {domain}")
                print(f"Error: {result.error_message}")
                failed_lookups += 1
            print("-" * 40 + "\n")

        logger.info(
             f"Application run finished. Successful lookups: {successful_lookups}, Failed lookups: {failed_lookups}"
        )
        print(f"\nProcessing complete. Success: {successful_lookups}, Failures: {failed_lookups}")


# --- Main Execution / Configuration Loading ---

def main() -> None:
    """Parses arguments, sets up components, and runs the application."""
    parser = argparse.ArgumentParser(description="Perform WHOIS lookups for domains listed in a file.")
    parser.add_argument(
        "-f", "--file",
        default=DEFAULT_INPUT_FILENAME,
        dest="filepath",
        help=f"Path to the input file containing domain names (default: {DEFAULT_INPUT_FILENAME})"
    )
    parser.add_argument(
        "-s", "--server",
        default=DEFAULT_WHOIS_SERVER,
        help=f"WHOIS server hostname (default: {DEFAULT_WHOIS_SERVER})"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=DEFAULT_WHOIS_PORT,
        help=f"WHOIS server port (default: {DEFAULT_WHOIS_PORT})"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=DEFAULT_SOCKET_TIMEOUT,
        help=f"Socket connection/read timeout in seconds (default: {DEFAULT_SOCKET_TIMEOUT})"
    )

    args = parser.parse_args()

    # --- Dependency Setup ---
    try:
        server_config = WhoisServerConfig(host=args.server, port=args.port)
        domain_reader = DomainFileReader(filepath=args.filepath)
        whois_client = WhoisClient(server_config=server_config, timeout=args.timeout)

        # --- Application Instantiation ---
        app = WhoisApp(domain_reader=domain_reader, whois_lookup=whois_client)

        # --- Run the Application ---
        app.run()

    except ValueError as e:
         # Catch configuration errors during component initialization
         logger.error(f"Configuration error: {e}")
         print(f"Configuration Error: {e}", file=sys.stderr)
    except Exception as e:
        # Catch-all for unexpected errors during setup
        logger.exception("An unexpected error occurred during application setup.")
        print(f"An unexpected setup error occurred: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
