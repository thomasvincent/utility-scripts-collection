# Utility Scripts Collection (OpsForge)

![Build Status](https://github.com/thomasvincent/utility-scripts-collection/actions/workflows/ci.yml/badge.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Code style: Google](https://img.shields.io/badge/code%20style-google-blue.svg)](https://google.github.io/styleguide/pyguide.html)

A forge of essential tools for DevOps engineers and system administrators. This package provides a set of command-line tools for common tasks including HTTP monitoring, DNS management, filesystem checks, and more.

## Features

- **HTTP Monitoring**: Check web servers for specific HTTP status codes (e.g., 500 errors) and send notifications
- **DNS Management**: Tools for retrieving zone information, searching records, and importing/exporting DNS data
- **Filesystem Utilities**: Check for read-only mounts and other filesystem issues on remote servers
- **Zenoss Integration**: Tools for interacting with Zenoss monitoring system
- **SoftLayer Integration**: Scripts for managing SoftLayer resources

## Installation

### From PyPI

```bash
pip install opsforge
```

### From Source

```bash
git clone https://github.com/thomasvincent/utility-scripts-collection.git
cd utility-scripts-collection
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/thomasvincent/utility-scripts-collection.git
cd utility-scripts-collection
make dev-install
```

This will:
- Install all development dependencies
- Set up pre-commit hooks
- Configure your development environment

## Configuration

OpsForge can be configured using a YAML configuration file. A sample configuration file is provided at `config.sample.yaml`. Copy this file to `config.yaml` and modify as needed:

```bash
cp config.sample.yaml config.yaml
```

Alternatively, all configuration options can be specified via environment variables or command-line arguments.

## Usage

### HTTP Status Monitoring

Monitor a web server for HTTP 500 errors:

```bash
opsforge-http500 --host example.com --email admin@example.com
```

Options:
- `--host`: The host to check
- `--port`: Port number (default: 80 for HTTP, 443 for HTTPS)
- `--scheme`: Protocol scheme (http or https)
- `--path`: Path to check (default: /)
- `--codes`: HTTP status codes to alert on (default: 500, 502, 503, 504)
- `--email`: Email address to send alerts to
- `--timeout`: Request timeout in seconds (default: 10)

### Read-only Filesystem Check

Check for read-only filesystems on a remote server:

```bash
opsforge-readonly --host server.example.com --user admin
```

Options:
- `--host`: Remote host to check
- `--user`: SSH username (default: root)
- `--port`: SSH port (default: 22)
- `--identity`: SSH identity file
- `--mount-table`: Mount table path (default: /proc/mounts)
- `--partition`: Pattern of partition to check (can be specified multiple times)
- `--exclude`: Pattern of partition to ignore
- `--exclude-type`: Filesystem types to exclude (can be specified multiple times)

### DNS Management

#### Get Zone Information

```bash
opsforge-dns get example.com
```

#### Search for Records in a File

```bash
opsforge-dns search example.com --file /path/to/dns/records.txt
```

#### Import TinyDNS Data

```bash
opsforge-dns tinydns --directory /service/tinydns
```

#### Search Google Sheets

```bash
opsforge-dns sheets "example.com" --key spreadsheet_key --credentials credentials.json
```

## Modules

The package is organized into the following modules:

- `opsforge.http`: HTTP monitoring tools
- `opsforge.dns`: DNS management tools
- `opsforge.filesystem`: Filesystem monitoring tools
- `opsforge.zenoss`: Zenoss integration tools
- `opsforge.softlayer`: SoftLayer integration tools
- `opsforge.monitoring`: General monitoring utilities
- `opsforge.common`: Shared utilities and helper functions

## Cleaned Up Scripts

The following scripts have been modernized to follow Python 3.10+ best practices and Google Python Style Guide:

### DNS Manager (`DNSScript/dns_manager.py`)
- Full type hints and dataclasses
- Proper error handling and logging
- Support for DNS queries, hosts file search, and TinyDNS import
- Comprehensive test coverage

### WHOIS Script (`WhoisScript/main.py`)
- Clean architecture with abstract base classes
- Type-safe implementation with dataclasses
- Proper socket handling with timeouts
- Full test suite

### HTTP 500 Checker (`NagiosPlugins/check_http500/check_http500_clean.py`)
- Nagios plugin compliant exit codes
- Email notification support
- Configurable SMTP settings
- Type hints throughout

All scripts include:
- ✅ Type hints for all functions
- ✅ Proper docstrings (Google style)
- ✅ Error handling with custom exceptions
- ✅ Logging configuration
- ✅ Command-line argument parsing with argparse
- ✅ Unit tests with pytest
- ✅ No hardcoded values
- ✅ Security best practices

## Development

### Testing

Run all tests:

```bash
make test
```

Run tests with coverage:

```bash
make coverage
```

Run all checks (lint, type checking, tests):

```bash
make check
```

### Code Style

This project follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) and uses:
- **Black** for code formatting (80 character line limit)
- **isort** for import sorting
- **Flake8** for linting
- **pylint** for additional style checking
- **mypy** for type checking

Format code:

```bash
make format
```

Check code style:

```bash
make lint
```

Run type checking:

```bash
make type
```

Run everything (format and all checks):

```bash
make all
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Run the pre-commit hooks on your changes (`pre-commit run --all-files`)
4. Commit your changes (`git commit -m 'feat: add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This project builds upon the original work by Thomas Vincent
- Thanks to all the contributors who have helped improve these tools