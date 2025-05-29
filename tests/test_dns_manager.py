#!/usr/bin/env python3
"""Tests for DNS manager module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "DNSScript"))

from dns_manager import DNSRecord, DNSManager


class TestDNSRecord:
    """Test DNSRecord dataclass."""
    
    def test_dns_record_creation(self):
        """Test creating a DNS record."""
        record = DNSRecord(
            name="example.com",
            record_type="A",
            value="192.168.1.1",
            ttl=300
        )
        assert record.name == "example.com"
        assert record.record_type == "A"
        assert record.value == "192.168.1.1"
        assert record.ttl == 300
    
    def test_dns_record_str(self):
        """Test string representation of DNS record."""
        record = DNSRecord(
            name="example.com",
            record_type="A",
            value="192.168.1.1",
            ttl=300
        )
        assert str(record) == "example.com A 192.168.1.1 (TTL: 300)"
        
        record_no_ttl = DNSRecord(
            name="example.com",
            record_type="A",
            value="192.168.1.1"
        )
        assert str(record_no_ttl) == "example.com A 192.168.1.1"


class TestDNSManager:
    """Test DNSManager class."""
    
    @pytest.fixture
    def dns_manager(self):
        """Create DNSManager instance."""
        return DNSManager()
    
    @patch('dns_manager.dns.resolver.Resolver')
    def test_get_zone_records_success(self, mock_resolver_class, dns_manager):
        """Test successful DNS zone record retrieval."""
        mock_resolver = Mock()
        mock_resolver_class.return_value = mock_resolver
        
        # Mock DNS response
        mock_answer = Mock()
        mock_answer.ttl = 300
        mock_rdata = Mock()
        mock_rdata.__str__ = Mock(return_value="192.168.1.1")
        mock_answer.__iter__ = Mock(return_value=iter([mock_rdata]))
        
        mock_resolver.resolve.return_value = mock_answer
        
        dns_manager.resolver = mock_resolver
        records = dns_manager.get_zone_records("example.com")
        
        assert len(records) > 0
        assert any(r.value == "192.168.1.1" for r in records)
    
    def test_search_hosts_file_found(self, dns_manager, tmp_path):
        """Test searching hosts file with matches."""
        hosts_content = """# Host file
127.0.0.1    localhost
192.168.1.100    myhost.local myhost
192.168.1.101    other.local
"""
        hosts_file = tmp_path / "hosts"
        hosts_file.write_text(hosts_content)
        
        matches = dns_manager.search_hosts_file("myhost", hosts_file)
        assert len(matches) == 1
        assert "myhost.local" in matches[0]
        assert "192.168.1.100" in matches[0]
    
    def test_search_hosts_file_not_found(self, dns_manager, tmp_path):
        """Test searching hosts file with no matches."""
        hosts_content = """127.0.0.1    localhost
192.168.1.101    other.local
"""
        hosts_file = tmp_path / "hosts"
        hosts_file.write_text(hosts_content)
        
        matches = dns_manager.search_hosts_file("notfound", hosts_file)
        assert len(matches) == 0
    
    def test_search_hosts_file_missing(self, dns_manager):
        """Test searching non-existent hosts file."""
        with pytest.raises(FileNotFoundError):
            dns_manager.search_hosts_file("test", Path("/nonexistent/hosts"))
    
    def test_import_tinydns_records(self, dns_manager, tmp_path):
        """Test importing TinyDNS records."""
        data_dir = tmp_path / "tinydns"
        data_dir.mkdir()
        
        tinydns_data = """+example.com:192.168.1.1:300
=host.example.com:192.168.1.2:
@example.com:mail.example.com:10:3600
'example.com:v=spf1 include:_spf.example.com ~all:
# Comment line
+another.com:10.0.0.1:86400
"""
        data_file = data_dir / "data"
        data_file.write_text(tinydns_data)
        
        records = dns_manager.import_tinydns_records(data_dir)
        
        assert len(records) == 5
        assert any(r.name == "example.com" and r.record_type == "A" for r in records)
        assert any(r.name == "example.com" and r.record_type == "MX" for r in records)
        assert any(r.name == "example.com" and r.record_type == "TXT" for r in records)
    
    def test_import_tinydns_no_data_file(self, dns_manager, tmp_path):
        """Test importing from TinyDNS directory without data file."""
        data_dir = tmp_path / "tinydns"
        data_dir.mkdir()
        
        with pytest.raises(FileNotFoundError):
            dns_manager.import_tinydns_records(data_dir)
    
    def test_parse_tinydns_line(self, dns_manager):
        """Test parsing individual TinyDNS lines."""
        # Test A record
        record = dns_manager._parse_tinydns_line("+example.com:192.168.1.1:300")
        assert record.name == "example.com"
        assert record.record_type == "A"
        assert record.value == "192.168.1.1"
        assert record.ttl == 300
        
        # Test MX record
        record = dns_manager._parse_tinydns_line("@example.com:mail.example.com:10:3600")
        assert record.name == "example.com"
        assert record.record_type == "MX"
        assert record.value == "mail.example.com"
        
        # Test invalid line
        record = dns_manager._parse_tinydns_line("")
        assert record is None
        
        # Test unknown record type
        record = dns_manager._parse_tinydns_line("Xexample.com:value")
        assert record is None


@pytest.mark.integration
class TestDNSManagerIntegration:
    """Integration tests for DNS manager."""
    
    def test_real_dns_query(self):
        """Test real DNS query (requires internet connection)."""
        dns_manager = DNSManager()
        
        # Query a well-known domain
        records = dns_manager.get_zone_records("google.com")
        
        # Should have at least some records
        assert len(records) > 0
        
        # Should have at least an A record
        a_records = [r for r in records if r.record_type == "A"]
        assert len(a_records) > 0