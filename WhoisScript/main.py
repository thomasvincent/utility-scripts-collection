import socket
from typing import List
from contextlib import closing  # Automatic resource management

# Constants
PORT = 43
BUFSIZE = 1024
LINEEND = b'\r\n'  # Use bytes for binary data
WHOIS_SERVER = "whois.internic.net"

def whois(domain: str, server: str = WHOIS_SERVER, port: int = PORT) -> str:
    """
    Performs a WHOIS search for a domain on the specified server and port.

    Args:
        domain (str): The domain name to look up.
        server (str, optional): The WHOIS server to connect to. Defaults to "whois.internic.net".
        port (int, optional): The port number of the WHOIS server. Defaults to 43.

    Returns:
        str: The WHOIS information for the domain, stripped of whitespace.
    """

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.connect((server, port))

        # Combine domain lookup string and line ending
        lookup = f"{domain}{LINEEND}".encode()
        s.sendall(lookup)

        readable, _, _ = select.select([s], [], [], 60)  # Wait for readability only
        if s in select.WRITABLE:
            raise ConnectionError("Unexpected writable state after sending lookup")

        response = b''
        while s in readable:
            data = s.recv(BUFSIZE)
            response += data
            if not data:
                break  # Connection closed

    return response.decode().strip()  # Decode and strip whitespace

def main() -> None:
    """
    Reads a list of domains from a file and performs WHOIS lookups for each one.

    Raises:
        FileNotFoundError: If the specified input file is not found.
    """

    try:
        with open(FILEPATH) as inputfile:
            domains: List[str] = [line.rstrip() for line in inputfile]  # Type hint for clarity
    except FileNotFoundError:
        print(f"Error: Input file '{FILEPATH}' not found.")
        return

    for domain in domains:
        print(f"WHOIS for {domain}:")
        whois_info = whois(domain)
        print(whois_info)

if __name__ == "__main__":
    main()
