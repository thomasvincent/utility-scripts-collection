"""
HTTP 500 (and other status codes) monitoring tool.

This module provides a tool for monitoring web servers for specific HTTP status codes,
such as 500 errors, and sending notifications when these conditions occur.

Typical usage:
    $ python -m opsforge.http.http500 --host example.com --email admin@example.com

For more options:
    $ python -m opsforge.http.http500 --help
"""

import logging
import os
import smtplib
import argparse
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Union, Tuple
from dataclasses import dataclass, field

import requests

from opsforge.common.logging import setup_logging, get_logger
from opsforge.common.exceptions import (
    OpsForgeError,
    NetworkError,
    AuthenticationError,
)

# Get logger for this module
logger = get_logger(__name__)

# Constants
DEFAULT_TIMEOUT = 10  # seconds
MAX_ERROR_CONTENT_LENGTH = 500  # max chars for email body
DEFAULT_SMTP_PORT = 587  # Updated to a more secure default (TLS)
DEFAULT_SMTP_SERVER = "localhost"


# Domain / Value Objects
@dataclass(frozen=True)
class CheckTarget:
    """Specifies the server endpoint to check."""

    host: str
    port: int
    scheme: str  # 'http' or 'https'
    path: str = "/"  # Path to check
    headers: Dict[str, str] = field(default_factory=dict)  # Custom headers
    
    def get_url(self) -> str:
        """Constructs the full URL for the check."""
        return f"{self.scheme}://{self.host}:{self.port}{self.path}"


@dataclass(frozen=True)
class CheckResult:
    """Holds the result of an HTTP check."""

    target: CheckTarget
    success: bool
    status_code: Optional[int] = None
    content: Optional[str] = None
    error_message: Optional[str] = None
    response_time: Optional[float] = None  # Response time in seconds


@dataclass(frozen=True)
class SmtpConfig:
    """Configuration for SMTP server connection."""

    server: str
    port: int
    use_tls: bool
    sender_address: str
    username: Optional[str] = None
    password: Optional[str] = None  # Consider more secure ways in production


@dataclass(frozen=True)
class NotificationDetails:
    """Details needed for sending a notification."""

    recipient_email: str


# Custom Exceptions
class HttpCheckError(OpsForgeError):
    """Error during HTTP check execution."""

    def __init__(self, message: str = "HTTP check failed"):
        super().__init__(f"HTTP check error: {message}")


class NotificationError(OpsForgeError):
    """Error during notification sending."""

    def __init__(self, message: str = "Notification failed"):
        super().__init__(f"Notification error: {message}")


# Services / Interfaces
class HttpChecker:
    """Performs HTTP checks against a target."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, verify_ssl: bool = True):
        """
        Initialize the HTTP checker.
        
        Args:
            timeout: Request timeout in seconds.
            verify_ssl: Whether to verify SSL certificates.
        """
        self._timeout = timeout
        self._verify_ssl = verify_ssl

    def check(self, target: CheckTarget) -> CheckResult:
        """
        Performs a GET request to the target URL.

        Args:
            target: The target to check.

        Returns:
            CheckResult containing success status, code, content, or error.
        """
        url = target.get_url()
        logger.info(f"Checking URL: {url}")
        try:
            # Use a session for better connection reuse
            with requests.Session() as session:
                # Set default headers for the session
                session.headers.update({
                    'User-Agent': 'OpsForge HTTP Monitor/1.0',
                    **target.headers
                })
                
                # Send the request with timing
                response = session.get(
                    url, 
                    timeout=self._timeout,
                    verify=self._verify_ssl,
                )
                response_time = response.elapsed.total_seconds()
                
            logger.info(f"Check successful for {url}. Status: {response.status_code}, Time: {response_time:.2f}s")
            return CheckResult(
                target=target,
                success=True,
                status_code=response.status_code,
                content=response.text,
                response_time=response_time,
            )
        except requests.exceptions.Timeout:
            logger.error(f"Timeout occurred while checking {url}")
            return CheckResult(target=target, success=False, error_message="Request timed out")
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL verification error while checking {url}: {e}")
            return CheckResult(target=target, success=False, error_message=f"SSL verification error: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while checking {url}: {e}")
            return CheckResult(target=target, success=False, error_message=f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected error occurred during HTTP check for {url}: {e}")
            return CheckResult(target=target, success=False, error_message=f"HTTP request error: {e}")
        except Exception as e:
            logger.exception(f"An unexpected non-HTTP error occurred during check for {url}")
            return CheckResult(target=target, success=False, error_message=f"Unexpected error: {e}")


class Notifier:
    """Interface for notification services."""

    def notify(self, subject: str, body: str) -> None:
        """Sends a notification."""
        raise NotImplementedError("Subclasses must implement notify()")


class EmailNotifier(Notifier):
    """Sends notifications via email using SMTP."""

    def __init__(self, smtp_config: SmtpConfig, details: NotificationDetails):
        """
        Initialize with SMTP configuration and notification details.
        
        Args:
            smtp_config: SMTP server configuration.
            details: Notification details.
        """
        self._config = smtp_config
        self._details = details

    def notify(self, subject: str, body: str) -> None:
        """
        Sends an email notification.

        Args:
            subject: The email subject line.
            body: The email body text.

        Raises:
            NotificationError: If sending the email fails.
        """
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self._config.sender_address
        msg["To"] = self._details.recipient_email

        logger.info(f"Attempting to send email notification to {self._details.recipient_email}")

        try:
            # Use 'with' statement for automatic connection closing
            with smtplib.SMTP(self._config.server, self._config.port) as smtp:
                # Enable TLS if configured (recommended for security)
                if self._config.use_tls:
                    smtp.starttls()

                # Login only if username and password are provided
                if self._config.username and self._config.password:
                    logger.debug("Attempting SMTP login...")
                    smtp.login(self._config.username, self._config.password)
                    logger.debug("SMTP login successful.")
                else:
                    logger.debug("Proceeding without SMTP authentication.")

                # Send the email
                smtp.sendmail(
                    self._config.sender_address,
                    [self._details.recipient_email],
                    msg.as_string(),
                )
            logger.info("Notification email sent successfully.")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise AuthenticationError(f"SMTP authentication failed: {e}")
        except smtplib.SMTPException as e:
            logger.error(f"Failed to send email due to SMTP error: {e}")
            raise NotificationError(f"Failed to send email: {e}")
        except OSError as e:
            logger.error(f"Network error during SMTP connection: {e}")
            raise NetworkError(f"Network error during SMTP connection: {e}")
        except Exception as e:
            logger.exception("An unexpected error occurred during email notification")
            raise NotificationError(f"Unexpected error sending email: {e}")


# Application Service
class ServerMonitor:
    """Orchestrates server checking and notification."""

    def __init__(self, checker: HttpChecker, notifier: Notifier, alert_codes: List[int]):
        """
        Initialize with HTTP checker, notifier, and alert codes.
        
        Args:
            checker: HTTP checker to use.
            notifier: Notifier to use for alerts.
            alert_codes: List of status codes to trigger alerts.
        """
        self._checker = checker
        self._notifier = notifier
        self._alert_codes = set(alert_codes)  # Use a set for faster lookups

    def run_check_and_notify(self, target: CheckTarget) -> CheckResult:
        """
        Runs the check and sends notification if an alert code is matched.
        
        Args:
            target: The target to check.
            
        Returns:
            The CheckResult from the checker.
        """
        result = self._checker.check(target)

        if not result.success:
            logger.warning(f"Check failed for {target.get_url()}: {result.error_message}")
            return result  # Don't proceed if the check itself failed

        if result.status_code is None:
            logger.warning(f"Check succeeded but no status code received for {target.get_url()}")
            return result  # Cannot compare status code if none exists

        if result.status_code in self._alert_codes:
            logger.warning(
                f"Alert triggered for {target.get_url()}: "
                f"Status code {result.status_code} matched target codes."
            )
            subject = f"🚨 Server Alert ({result.status_code}) on {target.host}"
            
            # Include response time if available
            response_time_info = ""
            if result.response_time is not None:
                response_time_info = f"**Response Time:** {result.response_time:.2f}s\n"
                
            body = f"""
            An alert condition was detected on {target.get_url()}:

            **Status Code:** {result.status_code}
            **Timestamp:** {logging.Formatter().formatTime(logging.LogRecord(None, None, "", 0, "", (), None, None))}
            {response_time_info}
            **Response Content Snippet:**
            ```
            {(result.content or "")[:MAX_ERROR_CONTENT_LENGTH]}
            {'...' if result.content and len(result.content) > MAX_ERROR_CONTENT_LENGTH else ''}
            ```
            """
            try:
                self._notifier.notify(subject, body.strip())
            except NotificationError as e:
                # Log the failure, but the program continues
                logger.error(f"Failed to send notification for {target.get_url()}: {e}")
        else:
            logger.info(
                f"Check OK for {target.get_url()}. "
                f"Status code {result.status_code} is not in alert list."
            )
            
        return result


# Configuration Loading
def load_smtp_config_from_env() -> SmtpConfig:
    """
    Loads SMTP configuration securely from environment variables.
    
    Returns:
        SmtpConfig object with SMTP server configuration.
    """
    username = os.getenv("OPSFORGE_SMTP_USER") or os.getenv("SMTP_USER")
    password = os.getenv("OPSFORGE_SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD")

    # Determine default sender address
    default_sender = f"opsforge@{os.uname().nodename}" if username else "opsforge@example.com"

    # Note: Default to TLS enabled for security
    return SmtpConfig(
        server=os.getenv("OPSFORGE_SMTP_SERVER", DEFAULT_SMTP_SERVER),
        port=int(os.getenv("OPSFORGE_SMTP_PORT", DEFAULT_SMTP_PORT)),
        use_tls=os.getenv("OPSFORGE_SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
        sender_address=os.getenv("OPSFORGE_SMTP_FROM", default_sender),
        username=username,
        password=password,
    )


def main() -> None:
    """Parses arguments, sets up components, and runs the check."""
    # Set up logging
    setup_logging(log_level=os.getenv("OPSFORGE_LOG_LEVEL", "INFO"))
    
    parser = argparse.ArgumentParser(description="Monitor HTTP status codes on a server and notify via email.")
    parser.add_argument("--email", required=True, help="Destination email address for notifications")
    parser.add_argument("--host", required=True, help="Host address (e.g., example.com or IP) to check")
    parser.add_argument("--port", type=int, default=None, help="Port number (default: 80 for http, 443 for https)")
    parser.add_argument(
        "--scheme", 
        choices=["http", "https"], 
        default=None, 
        help="Protocol scheme (default: http for port 80, https for 443/other)"
    )
    parser.add_argument(
        "--path",
        default="/",
        help="Path to check (default: /)"
    )
    parser.add_argument(
        "--header",
        action="append",
        dest="headers",
        help="Add custom HTTP header (format: 'Header-Name: value'). Can be used multiple times."
    )
    parser.add_argument(
        "--codes",
        type=int,
        nargs="+",
        default=[500, 502, 503, 504],  # Default to common server error codes
        dest="alert_codes",
        help="HTTP status codes to trigger alerts (default: 500 502 503 504)",
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=DEFAULT_TIMEOUT, 
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification"
    )

    args = parser.parse_args()

    # Determine scheme and port defaults if not provided
    port = args.port
    scheme = args.scheme
    if scheme is None:
        if port == 443:
            scheme = "https"
        else:
            scheme = "http"  # Default to http if scheme unspecified and port isn't 443
    if port is None:
        port = 443 if scheme == "https" else 80  # Default port based on final scheme
        
    # Parse headers if provided
    headers = {}
    if args.headers:
        for header in args.headers:
            try:
                name, value = header.split(":", 1)
                headers[name.strip()] = value.strip()
            except ValueError:
                logger.warning(f"Invalid header format: {header}. Should be 'Name: value'")

    # Dependency Setup
    try:
        check_target = CheckTarget(host=args.host, port=port, scheme=scheme, path=args.path, headers=headers)
        smtp_config = load_smtp_config_from_env()
        notification_details = NotificationDetails(recipient_email=args.email)

        http_checker = HttpChecker(timeout=args.timeout, verify_ssl=not args.no_verify_ssl)
        email_notifier = EmailNotifier(smtp_config=smtp_config, details=notification_details)

        monitor = ServerMonitor(
            checker=http_checker, notifier=email_notifier, alert_codes=args.alert_codes
        )

        # Run the Monitor
        monitor.run_check_and_notify(check_target)
        logger.info("Monitoring check completed.")

    except OpsForgeError as e:
        logger.error(f"Configuration or setup error: {e}")
    except Exception as e:
        logger.exception("An unexpected error occurred in the main execution block.")


if __name__ == "__main__":
    main()