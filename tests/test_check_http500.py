#!/usr/bin/env python3
"""Tests for check_http500 Nagios plugin."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).parent.parent / "NagiosPlugins" / "check_http500"))

from check_http500_clean import (
    HTTPChecker, EmailNotifier, main,
    OK, WARNING, CRITICAL, UNKNOWN
)


class TestHTTPChecker:
    """Test HTTPChecker class."""
    
    def test_init_http(self):
        """Test initialization with HTTP."""
        checker = HTTPChecker("example.com", 80)
        assert checker.host == "example.com"
        assert checker.port == 80
        assert checker.protocol == "http"
        assert checker.url == "http://example.com:80/"
    
    def test_init_https(self):
        """Test initialization with HTTPS."""
        checker = HTTPChecker("example.com", 443)
        assert checker.protocol == "https"
        assert checker.url == "https://example.com:443/"
    
    @patch('check_http500_clean.urlopen')
    def test_check_success(self, mock_urlopen):
        """Test successful HTTP check."""
        mock_response = Mock()
        mock_response.read.return_value = b"OK"
        mock_urlopen.return_value = mock_response
        
        checker = HTTPChecker("example.com")
        exit_code, message, error_content = checker.check()
        
        assert exit_code == OK
        assert "OK" in message
        assert error_content is None
    
    @patch('check_http500_clean.urlopen')
    def test_check_http_500(self, mock_urlopen):
        """Test HTTP 500 error detection."""
        mock_error = HTTPError(
            url="http://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None
        )
        mock_error.read = Mock(return_value=b"Server error details")
        mock_urlopen.side_effect = mock_error
        
        checker = HTTPChecker("example.com")
        exit_code, message, error_content = checker.check()
        
        assert exit_code == CRITICAL
        assert "HTTP 500" in message
        assert error_content == "Server error details"
    
    @patch('check_http500_clean.urlopen')
    def test_check_http_404(self, mock_urlopen):
        """Test non-500 HTTP error."""
        mock_error = HTTPError(
            url="http://example.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )
        mock_urlopen.side_effect = mock_error
        
        checker = HTTPChecker("example.com")
        exit_code, message, error_content = checker.check()
        
        assert exit_code == WARNING
        assert "HTTP 404" in message
        assert error_content is None
    
    @patch('check_http500_clean.urlopen')
    def test_check_connection_error(self, mock_urlopen):
        """Test connection error."""
        mock_urlopen.side_effect = URLError("Connection refused")
        
        checker = HTTPChecker("example.com")
        exit_code, message, error_content = checker.check()
        
        assert exit_code == CRITICAL
        assert "Cannot connect" in message
        assert error_content is None
    
    @patch('check_http500_clean.urlopen')
    def test_check_unexpected_error(self, mock_urlopen):
        """Test unexpected error handling."""
        mock_urlopen.side_effect = Exception("Unexpected error")
        
        checker = HTTPChecker("example.com")
        exit_code, message, error_content = checker.check()
        
        assert exit_code == UNKNOWN
        assert "UNKNOWN" in message
        assert error_content is None


class TestEmailNotifier:
    """Test EmailNotifier class."""
    
    def test_init(self):
        """Test initialization."""
        notifier = EmailNotifier()
        assert notifier.smtp_host == "localhost"
        assert notifier.smtp_port == 25
        assert notifier.from_email == "nagios@localhost"
    
    @patch('check_http500_clean.smtplib.SMTP')
    def test_send_alert_success(self, mock_smtp_class):
        """Test successful email sending."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        notifier = EmailNotifier()
        result = notifier.send_alert(
            "test@example.com",
            "example.com",
            "Error content"
        )
        
        assert result is True
        mock_smtp.sendmail.assert_called_once()
        
        # Check email details
        call_args = mock_smtp.sendmail.call_args[0]
        assert call_args[0] == "nagios@localhost"
        assert call_args[1] == ["test@example.com"]
        assert "HTTP 500 Error: example.com" in call_args[2]
    
    @patch('check_http500_clean.smtplib.SMTP')
    def test_send_alert_failure(self, mock_smtp_class):
        """Test email sending failure."""
        mock_smtp_class.side_effect = Exception("SMTP error")
        
        notifier = EmailNotifier()
        result = notifier.send_alert(
            "test@example.com",
            "example.com",
            "Error content"
        )
        
        assert result is False


class TestMain:
    """Test main function."""
    
    @patch('sys.argv', ['check_http500.py', '--host', 'example.com', 
                        '--email', 'test@example.com'])
    @patch('check_http500_clean.HTTPChecker')
    @patch('check_http500_clean.EmailNotifier')
    def test_main_success(self, mock_notifier_class, mock_checker_class):
        """Test main function with successful check."""
        # Mock checker
        mock_checker = Mock()
        mock_checker.check.return_value = (OK, "OK - Service is up", None)
        mock_checker_class.return_value = mock_checker
        
        # Mock notifier
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == OK
        mock_notifier.send_alert.assert_not_called()
    
    @patch('sys.argv', ['check_http500.py', '--host', 'example.com',
                        '--email', 'test@example.com'])
    @patch('check_http500_clean.HTTPChecker')
    @patch('check_http500_clean.EmailNotifier')
    def test_main_http500(self, mock_notifier_class, mock_checker_class):
        """Test main function with HTTP 500 error."""
        # Mock checker
        mock_checker = Mock()
        mock_checker.check.return_value = (
            CRITICAL, 
            "CRITICAL - HTTP 500 error", 
            "Error details"
        )
        mock_checker_class.return_value = mock_checker
        
        # Mock notifier
        mock_notifier = Mock()
        mock_notifier.send_alert.return_value = True
        mock_notifier_class.return_value = mock_notifier
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == CRITICAL
        mock_notifier.send_alert.assert_called_once_with(
            "test@example.com", "example.com", "Error details"
        )
    
    @patch('sys.argv', ['check_http500.py', '--host', 'example.com',
                        '--email', 'invalid-email'])
    def test_main_invalid_email(self):
        """Test main function with invalid email."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == UNKNOWN