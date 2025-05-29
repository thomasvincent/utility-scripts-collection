#!/usr/bin/env python3
"""Tests for the WHOIS script."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import socket

sys.path.insert(0, str(Path(__file__).parent.parent / "WhoisScript"))

from main import (
    WhoisServerConfig, WhoisResult, DomainFileReader, WhoisClient,
    WhoisApp, DomainReadError, WhoisLookupError,
    DEFAULT_WHOIS_PORT, DEFAULT_WHOIS_SERVER, DEFAULT_SOCKET_TIMEOUT
)


class TestWhoisServerConfig:
    """Test WhoisServerConfig dataclass."""
    
    def test_creation(self):
        """Test creating a WhoisServerConfig."""
        config = WhoisServerConfig(host="whois.example.com", port=43)
        assert config.host == "whois.example.com"
        assert config.port == 43
    
    def test_immutable(self):
        """Test that WhoisServerConfig is immutable."""
        config = WhoisServerConfig(host="whois.example.com", port=43)
        with pytest.raises(AttributeError):
            config.host = "new.host"


class TestWhoisResult:
    """Test WhoisResult dataclass."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        result = WhoisResult(
            domain="example.com",
            success=True,
            response="WHOIS data here"
        )
        assert result.domain == "example.com"
        assert result.success is True
        assert result.response == "WHOIS data here"
        assert result.error_message is None
    
    def test_failure_result(self):
        """Test creating a failure result."""
        result = WhoisResult(
            domain="example.com",
            success=False,
            error_message="Connection failed"
        )
        assert result.domain == "example.com"
        assert result.success is False
        assert result.response is None
        assert result.error_message == "Connection failed"


class TestDomainFileReader:
    """Test DomainFileReader class."""
    
    def test_init_with_empty_filepath(self):
        """Test initialization with empty filepath."""
        with pytest.raises(ValueError):
            DomainFileReader("")
    
    def test_read_domains_success(self):
        """Test successfully reading domains from file."""
        mock_file_content = """example.com
test.org

another-domain.net
"""
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            reader = DomainFileReader("domains.txt")
            domains = reader.read_domains()
            
        assert domains == ["example.com", "test.org", "another-domain.net"]
    
    def test_read_domains_file_not_found(self):
        """Test handling file not found."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            reader = DomainFileReader("nonexistent.txt")
            with pytest.raises(DomainReadError) as exc_info:
                reader.read_domains()
            assert "not found" in str(exc_info.value)
    
    def test_read_domains_io_error(self):
        """Test handling IO error."""
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            reader = DomainFileReader("domains.txt")
            with pytest.raises(DomainReadError) as exc_info:
                reader.read_domains()
            assert "Error reading file" in str(exc_info.value)
    
    def test_read_domains_empty_file(self):
        """Test reading empty file."""
        with patch("builtins.open", mock_open(read_data="")):
            reader = DomainFileReader("domains.txt")
            domains = reader.read_domains()
            assert domains == []


class TestWhoisClient:
    """Test WhoisClient class."""
    
    def test_init_with_none_config(self):
        """Test initialization with None config."""
        with pytest.raises(ValueError):
            WhoisClient(None)
    
    @patch('socket.socket')
    def test_lookup_success(self, mock_socket_class):
        """Test successful WHOIS lookup."""
        # Mock socket instance
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.recv.side_effect = [
            b"Domain Name: EXAMPLE.COM\n",
            b"Registrar: Example Registrar\n",
            b""  # End of data
        ]
        
        config = WhoisServerConfig(host="whois.test", port=43)
        client = WhoisClient(config)
        result = client.lookup("example.com")
        
        assert result.success is True
        assert result.domain == "example.com"
        assert "Domain Name: EXAMPLE.COM" in result.response
        assert "Registrar: Example Registrar" in result.response
        
        # Verify socket operations
        mock_socket.settimeout.assert_called_with(DEFAULT_SOCKET_TIMEOUT)
        mock_socket.connect.assert_called_with(("whois.test", 43))
        mock_socket.sendall.assert_called()
    
    def test_lookup_empty_domain(self):
        """Test lookup with empty domain."""
        config = WhoisServerConfig(host="whois.test", port=43)
        client = WhoisClient(config)
        result = client.lookup("")
        
        assert result.success is False
        assert result.error_message == "Domain name cannot be empty"
    
    @patch('socket.socket')
    def test_lookup_timeout(self, mock_socket_class):
        """Test WHOIS lookup timeout."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = socket.timeout("Connection timed out")
        
        config = WhoisServerConfig(host="whois.test", port=43)
        client = WhoisClient(config, timeout=5.0)
        result = client.lookup("example.com")
        
        assert result.success is False
        assert "Timeout after 5.0s" in result.error_message
    
    @patch('socket.socket')
    def test_lookup_dns_failure(self, mock_socket_class):
        """Test WHOIS lookup with DNS failure."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = socket.gaierror("Name resolution failed")
        
        config = WhoisServerConfig(host="whois.invalid", port=43)
        client = WhoisClient(config)
        result = client.lookup("example.com")
        
        assert result.success is False
        assert "DNS lookup failed" in result.error_message
    
    @patch('socket.socket')
    def test_lookup_connection_refused(self, mock_socket_class):
        """Test WHOIS lookup with connection refused."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = socket.error("Connection refused")
        
        config = WhoisServerConfig(host="whois.test", port=43)
        client = WhoisClient(config)
        result = client.lookup("example.com")
        
        assert result.success is False
        assert "Socket error" in result.error_message


class TestWhoisApp:
    """Test WhoisApp class."""
    
    def test_init_with_none_dependencies(self):
        """Test initialization with None dependencies."""
        mock_reader = Mock()
        mock_lookup = Mock()
        
        with pytest.raises(ValueError):
            WhoisApp(None, mock_lookup)
        
        with pytest.raises(ValueError):
            WhoisApp(mock_reader, None)
    
    def test_run_success(self, capsys):
        """Test successful application run."""
        # Mock dependencies
        mock_reader = Mock()
        mock_reader.read_domains.return_value = ["example.com", "test.org"]
        
        mock_lookup = Mock()
        mock_lookup.lookup.side_effect = [
            WhoisResult(
                domain="example.com",
                success=True,
                response="Example.com WHOIS data"
            ),
            WhoisResult(
                domain="test.org",
                success=False,
                error_message="Connection failed"
            )
        ]
        
        # Run app
        app = WhoisApp(mock_reader, mock_lookup)
        app.run()
        
        # Check output
        captured = capsys.readouterr()
        assert "WHOIS lookup successful for: example.com" in captured.out
        assert "Example.com WHOIS data" in captured.out
        assert "WHOIS lookup FAILED for: test.org" in captured.out
        assert "Connection failed" in captured.out
        assert "Success: 1, Failures: 1" in captured.out
    
    def test_run_domain_read_error(self, capsys):
        """Test application run with domain read error."""
        mock_reader = Mock()
        mock_reader.read_domains.side_effect = DomainReadError("File not found")
        
        mock_lookup = Mock()
        
        app = WhoisApp(mock_reader, mock_lookup)
        app.run()
        
        captured = capsys.readouterr()
        assert "Could not read domains" in captured.err
        mock_lookup.lookup.assert_not_called()
    
    def test_run_no_domains(self, capsys):
        """Test application run with no domains."""
        mock_reader = Mock()
        mock_reader.read_domains.return_value = []
        
        mock_lookup = Mock()
        
        app = WhoisApp(mock_reader, mock_lookup)
        app.run()
        
        captured = capsys.readouterr()
        assert "No domains found" in captured.out
        mock_lookup.lookup.assert_not_called()


@pytest.mark.integration
class TestWhoisIntegration:
    """Integration tests for WHOIS functionality."""
    
    def test_real_whois_lookup(self):
        """Test real WHOIS lookup (requires internet connection)."""
        config = WhoisServerConfig(host=DEFAULT_WHOIS_SERVER, port=DEFAULT_WHOIS_PORT)
        client = WhoisClient(config)
        
        # Use a well-known domain
        result = client.lookup("google.com")
        
        assert result.success is True
        assert result.response is not None
        assert "google" in result.response.lower()