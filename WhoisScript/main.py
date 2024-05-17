import socket
from typing import List
from contextlib import closing

# Constants (with type hints and moved to the top for clarity)
PORT: int = 43
BUFSIZE: int = 1024
LINEEND: bytes = b'\r\n'
WHOIS_SERVER: str = "whois.internic.net"
FILEPATH: str = "domains.txt"  # Explicitly define the input file

def whois(domain: str, server: str = WHOIS_SERVER, port: int = PORT) -> str:
    """Performs a WHOIS search for a domain."""

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        try:
            s.connect((server, port))
            lookup = f"{domain}{LINEEND}".encode()
            s.sendall(lookup)

            response = b""
            while True:
                data = s.recv(BUFSIZE)
                if not data:
                    break
                response += data
        except socket.timeout:
            raise TimeoutError(f"Timeout occurred while connecting to {server}:{port}")
        except socket.error as e:
            raise ConnectionError(f"Error connecting to {server}:{port}: {e}")

    return response.decode().strip()

def main() -> None:
    """Reads domains from a file and performs WHOIS lookups."""

    try:
        with open(FILEPATH, "r") as input_file:
            domains: List[str] = [line.strip() for line in input_file if line.strip()]
    except FileNotFoundError:
        print(f"Error: Input file '{FILEPATH}' not found.")
        return

    for domain in domains:
        try:
            whois_info = whois(domain)
            print(f"\nWHOIS for {domain}:")
            print(whois_info)
        except (TimeoutError, ConnectionError) as e:
            print(f"Error during WHOIS for {domain}: {e}")

if __name__ == "__main__":
    main()
