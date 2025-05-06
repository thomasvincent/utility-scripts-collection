"""
Unit tests for the HTTP 500 monitoring module.
"""

import unittest
from unittest.mock import patch, MagicMock

from utility_scripts.http.http500 import (
    HttpChecker,
    CheckTarget,
    CheckResult,
    SmtpConfig,
    NotificationDetails,
    EmailNotifier,
    ServerMonitor,
)

class TestCheckTarget(unittest.TestCase):
    """Tests for the CheckTarget class."""
    
    def test_get_url(self):
        """Test that get_url correctly constructs a URL."""
        target = CheckTarget(host="example.com", port=80, scheme="http", path="/test")
        self.assertEqual(target.get_url(), "http://example.com:80/test")
        
        # Test HTTPS
        target = CheckTarget(host="example.com", port=443, scheme="https")
        self.assertEqual(target.get_url(), "https://example.com:443/")


class TestHttpChecker(unittest.TestCase):
    """Tests for the HttpChecker class."""
    
    @patch('utility_scripts.http.http500.requests.get')
    def test_check_success(self, mock_get):
        """Test successful HTTP check."""
        # Configure the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_get.return_value = mock_response
        
        # Create the checker and target
        checker = HttpChecker(timeout=5)
        target = CheckTarget(host="example.com", port=80, scheme="http")
        
        # Perform the check
        result = checker.check(target)
        
        # Verify the result
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, "OK")
        self.assertIsNone(result.error_message)
        
        # Verify the mock was called correctly
        mock_get.assert_called_once_with("http://example.com:80/", timeout=5)
    
    @patch('utility_scripts.http.http500.requests.get')
    def test_check_error(self, mock_get):
        """Test HTTP check with error."""
        # Configure the mock to raise an exception
        mock_get.side_effect = Exception("Test error")
        
        # Create the checker and target
        checker = HttpChecker(timeout=5)
        target = CheckTarget(host="example.com", port=80, scheme="http")
        
        # Perform the check
        result = checker.check(target)
        
        # Verify the result
        self.assertFalse(result.success)
        self.assertIsNone(result.status_code)
        self.assertIsNone(result.content)
        self.assertEqual(result.error_message, "Unexpected error: Test error")


class TestEmailNotifier(unittest.TestCase):
    """Tests for the EmailNotifier class."""
    
    @patch('utility_scripts.http.http500.smtplib.SMTP')
    def test_notify_success(self, mock_smtp):
        """Test successful email notification."""
        # Configure SMTP mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Create the notifier
        smtp_config = SmtpConfig(
            server="smtp.example.com",
            port=25,
            use_tls=False,
            sender_address="sender@example.com"
        )
        details = NotificationDetails(recipient_email="recipient@example.com")
        notifier = EmailNotifier(smtp_config, details)
        
        # Send notification
        notifier.notify("Test Subject", "Test Body")
        
        # Verify SMTP was called correctly
        mock_smtp.assert_called_once_with("smtp.example.com", 25)
        mock_smtp_instance.sendmail.assert_called_once()
        # First arg should be sender
        self.assertEqual(mock_smtp_instance.sendmail.call_args[0][0], "sender@example.com")
        # Second arg should be recipient list
        self.assertEqual(mock_smtp_instance.sendmail.call_args[0][1], ["recipient@example.com"])
        # Don't check the exact content of the third arg (email body)


class TestServerMonitor(unittest.TestCase):
    """Tests for the ServerMonitor class."""
    
    def test_run_check_and_notify_no_alert(self):
        """Test that no notification is sent when status code is not in alert list."""
        # Create mocks
        mock_checker = MagicMock()
        mock_notifier = MagicMock()
        
        # Configure mock checker to return a 200 status
        mock_result = CheckResult(
            target=CheckTarget(host="example.com", port=80, scheme="http"),
            success=True,
            status_code=200,
            content="OK"
        )
        mock_checker.check.return_value = mock_result
        
        # Create monitor
        monitor = ServerMonitor(checker=mock_checker, notifier=mock_notifier, alert_codes=[500])
        
        # Run monitor
        monitor.run_check_and_notify(mock_result.target)
        
        # Verify checker was called
        mock_checker.check.assert_called_once()
        
        # Verify notifier was NOT called
        mock_notifier.notify.assert_not_called()
    
    def test_run_check_and_notify_with_alert(self):
        """Test that notification is sent when status code is in alert list."""
        # Create mocks
        mock_checker = MagicMock()
        mock_notifier = MagicMock()
        
        # Configure mock checker to return a 500 status
        mock_result = CheckResult(
            target=CheckTarget(host="example.com", port=80, scheme="http"),
            success=True,
            status_code=500,
            content="Internal Server Error"
        )
        mock_checker.check.return_value = mock_result
        
        # Create monitor
        monitor = ServerMonitor(checker=mock_checker, notifier=mock_notifier, alert_codes=[500])
        
        # Run monitor
        monitor.run_check_and_notify(mock_result.target)
        
        # Verify checker was called
        mock_checker.check.assert_called_once()
        
        # Verify notifier was called
        mock_notifier.notify.assert_called_once()
        # First arg should be a subject containing 500
        self.assertIn("500", mock_notifier.notify.call_args[0][0])
        # Second arg should be a body containing the content
        self.assertIn("Internal Server Error", mock_notifier.notify.call_args[0][1])


if __name__ == '__main__':
    unittest.main()