#!/usr/bin/env python3
"""Nagios plugin to check for HTTP 500 errors and send email alerts.

This plugin checks a specified host/port for HTTP 500 errors and sends
email notifications when detected. It follows Nagios plugin conventions
for exit codes.

Exit codes:
    0 - OK: Service is responding normally
    1 - WARNING: Not used in this plugin
    2 - CRITICAL: HTTP 500 error detected
    3 - UNKNOWN: Invalid parameters or other errors
"""

import argparse
import logging
import smtplib
import sys
from email.mime.text import MIMEText
from typing import Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Nagios exit codes
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

# Default configuration
DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 30
DEFAULT_SMTP_HOST = 'localhost'
DEFAULT_SMTP_PORT = 25
DEFAULT_FROM_EMAIL = 'nagios@localhost'


class HTTPChecker:
    """Checks HTTP endpoints for 500 errors."""
    
    def __init__(self, host: str, port: int = DEFAULT_PORT, 
                 timeout: int = DEFAULT_TIMEOUT):
        """Initialize HTTP checker.
        
        Args:
            host: Hostname or IP address to check
            port: Port number (default: 80)
            timeout: Request timeout in seconds (default: 30)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.protocol = 'https' if port == 443 else 'http'
        self.url = f"{self.protocol}://{host}:{port}/"
    
    def check(self) -> Tuple[int, str, Optional[str]]:
        """Check the HTTP endpoint.
        
        Returns:
            Tuple of (exit_code, message, error_content)
        """
        try:
            request = Request(self.url)
            response = urlopen(request, timeout=self.timeout)
            content = response.read()
            return (OK, f"OK - {self.url} is responding normally", None)
            
        except HTTPError as e:
            if e.code == 500:
                error_content = e.read().decode('utf-8', errors='replace')
                return (CRITICAL, 
                        f"CRITICAL - HTTP 500 error from {self.url}", 
                        error_content)
            else:
                return (WARNING, 
                        f"WARNING - HTTP {e.code} error from {self.url}", 
                        None)
                        
        except URLError as e:
            return (CRITICAL, 
                    f"CRITICAL - Cannot connect to {self.url}: {e.reason}", 
                    None)
                    
        except Exception as e:
            logger.exception(f"Unexpected error checking {self.url}")
            return (UNKNOWN, 
                    f"UNKNOWN - Error checking {self.url}: {str(e)}", 
                    None)


class EmailNotifier:
    """Sends email notifications for HTTP 500 errors."""
    
    def __init__(self, smtp_host: str = DEFAULT_SMTP_HOST,
                 smtp_port: int = DEFAULT_SMTP_PORT,
                 from_email: str = DEFAULT_FROM_EMAIL):
        """Initialize email notifier.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            from_email: Sender email address
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
    
    def send_alert(self, to_email: str, host: str, 
                   error_content: str) -> bool:
        """Send HTTP 500 alert email.
        
        Args:
            to_email: Recipient email address
            host: The host that returned 500 error
            error_content: The error response body
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            msg = MIMEText(error_content)
            msg['Subject'] = f'HTTP 500 Error: {host}'
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.sendmail(self.from_email, [to_email], msg.as_string())
                
            logger.info(f"Alert email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


def main():
    """Main entry point for the check_http500 plugin."""
    parser = argparse.ArgumentParser(
        description='Nagios plugin to check for HTTP 500 errors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --host example.com --email alerts@example.com
  %(prog)s --host example.com --port 8080 --email alerts@example.com
  %(prog)s --host example.com --port 443 --email alerts@example.com --timeout 60
        """
    )
    
    parser.add_argument(
        '--host',
        required=True,
        help='Hostname or IP address to check'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=DEFAULT_PORT,
        help=f'Port number (default: {DEFAULT_PORT})'
    )
    
    parser.add_argument(
        '--email',
        required=True,
        help='Email address for notifications'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f'Request timeout in seconds (default: {DEFAULT_TIMEOUT})'
    )
    
    parser.add_argument(
        '--smtp-host',
        default=DEFAULT_SMTP_HOST,
        help=f'SMTP server hostname (default: {DEFAULT_SMTP_HOST})'
    )
    
    parser.add_argument(
        '--smtp-port',
        type=int,
        default=DEFAULT_SMTP_PORT,
        help=f'SMTP server port (default: {DEFAULT_SMTP_PORT})'
    )
    
    parser.add_argument(
        '--from-email',
        default=DEFAULT_FROM_EMAIL,
        help=f'Sender email address (default: {DEFAULT_FROM_EMAIL})'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate email address format
    if '@' not in args.email:
        print(f"UNKNOWN - Invalid email address: {args.email}")
        sys.exit(UNKNOWN)
    
    # Initialize checker and notifier
    checker = HTTPChecker(args.host, args.port, args.timeout)
    notifier = EmailNotifier(args.smtp_host, args.smtp_port, args.from_email)
    
    # Perform check
    exit_code, message, error_content = checker.check()
    
    # Send email notification if HTTP 500 detected
    if exit_code == CRITICAL and error_content:
        notifier.send_alert(args.email, args.host, error_content)
    
    # Output result and exit with appropriate code
    print(message)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()