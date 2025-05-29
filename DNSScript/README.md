# DNS Script Module

A modern, Pythonic DNS record management tool with support for various DNS sources.

## Features

- Query DNS records for any domain
- Search for hostnames in local files (e.g., /etc/hosts)
- Import DNS records from TinyDNS data files
- Type-safe implementation with dataclasses
- Comprehensive error handling and logging
- Full test coverage

## Requirements

- Python 3.10+
- dnspython library

## Installation

```bash
pip install dnspython
```

## Usage

### Query DNS Records

```bash
python dns_manager.py --get example.com
```

### Search Hosts File

```bash
python dns_manager.py --search myhost --file /etc/hosts
```

### Import TinyDNS Records

```bash
python dns_manager.py --tinydns /service/tinydns
```

### Enable Verbose Output

```bash
python dns_manager.py --get example.com --verbose
```

## Development

### Running Tests

```bash
pytest tests/test_dns_manager.py
```

### Code Style

This module follows PEP 8 style guidelines and uses type hints throughout.

## Security Notes

- No passwords or credentials are stored in the code
- All file operations include proper permission checks
- Input validation prevents injection attacks
