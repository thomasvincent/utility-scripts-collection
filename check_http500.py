#!/usr/bin/env python3

import logging
import os
import smtplib
import argparse
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Union, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import requests # Keep requests import here

# --- Logging Configuration ---
# Consistent logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Get logger instance specifically for this module's operations
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_TIMEOUT = 10  # seconds
MAX_ERROR_CONTENT_LENGTH = 500 # Increased max chars for email body
DEFAULT_SMTP_PORT = 25
DEFAULT_SMTP_SERVER = "localhost"

# --- Domain / Value Objects ---

@dataclass(frozen=True)
class CheckTarget:
    """Specifies the server endpoint to check."""
    host: str
    port: int
    scheme: str # 'http' or 'https'

    def get_url(self) -> str:
        """Constructs the full URL for the check."""
        return f"{self.scheme}://{self.host}:{self.port}/"

@dataclass(frozen=True)
class CheckResult:
    """Holds the result of an HTTP check."""
    target: CheckTarget
    success: bool
    status_code: Optional[int] = None
    content: Optional[str] = None
    error_message: Optional[str] = None

@dataclass(frozen=True)
class SmtpConfig:
    """Configuration for SMTP server connection."""
    server: str
    port: int
    use_tls: bool
    sender_address: str
    username: Optional[str] = None
    password: Optional[str] = None # Consider more secure ways in production (secrets manager)

@dataclass(frozen=True)
class NotificationDetails:
    """Details needed for sending a notification."""
    recipient_email: str

# --- Custom Exceptions ---

class HttpCheckError(Exception):
    """Error during HTTP check execution."""
    pass

class NotificationError(Exception):
    """Error during notification sending."""
    pass

# --- Services / Interfaces ---

class HttpChecker:
    """Performs HTTP checks against a target."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self._timeout = timeout

    def check(self, target: CheckTarget) -> CheckResult:
        """
        Performs a GET request to the target URL.

        Returns:
            CheckResult containing success status, code, content, or error.
        """
        url = target.get_url()
        logger.info(f"Checking URL: {url}")
        try:
            response = requests.get(url, timeout=self._timeout)
            # Raise HTTPError for bad responses (4xx or 5xx) if needed,
            # but here we just capture the status code regardless.
            # response.raise_for_status()
            logger.info(f"Check successful for {url}. Status: {response.status_code}")
            return CheckResult(
                target=target,
                success=True,
                status_code=response.status_code,
                content=response.text
            )
        except requests.exceptions.Timeout:
            logger.error(f"Timeout occurred while checking {url}")
            return CheckResult(target=target, success=False, error_message="Request timed out")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while checking {url}: {e}")
            return CheckResult(target=target, success=False, error_message=f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected error occurred during HTTP check for {url}: {e}")
            # Capture generic request exceptions
            return CheckResult(target=target, success=False, error_message=f"HTTP request error: {e}")
        except Exception as e:
            # Catch any other unexpected errors during the check process
            logger.exception(f"An unexpected non-HTTP error occurred during check for {url}")
            return CheckResult(target=target, success=False, error_message=f"Unexpected error: {e}")


class Notifier(ABC):
    """Abstract base class for notification services."""

    @abstractmethod
    def notify(self, subject: str, body: str) -> None:
        """Sends a notification."""
        pass


class EmailNotifier(Notifier):
    """Sends notifications via email using SMTP."""

    def __init__(self, smtp_config: SmtpConfig, details: NotificationDetails):
        self._config = smtp_config
        self._details = details

    def notify(self, subject: str, body: str) -> None:
        """
        Sends an email notification.

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
                if self._config.use_tls:
                    # Initiate TLS connection securely
                    smtp.starttls() # Raises SMTPException if server doesn't support STARTTLS

                # Login only if username and password are provided
                if self._config.username and self._config.password:
                     logger.info("Attempting SMTP login...")
                     smtp.login(self._config.username, self._config.password)
                     logger.info("SMTP login successful.")
                else:
                     logger.info("Proceeding without SMTP authentication.")


                # Send the email
                smtp.sendmail(
                    self._config.sender_address,
                    [self._details.recipient_email], # Must be a list
                    msg.as_string()
                )
            logger.info("Notification email sent successfully.")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise NotificationError(f"SMTP authentication failed: {e}") from e
        except smtplib.SMTPException as e:
            # Catches various SMTP errors (connection, HELO, data, etc.)
            logger.error(f"Failed to send email due to SMTP error: {e}")
            raise NotificationError(f"Failed to send email: {e}") from e
        except OSError as e:
             # Catches potential network/socket errors during connection
             logger.error(f"Network error during SMTP connection: {e}")
             raise NotificationError(f"Network error during SMTP connection: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors during email sending
            logger.exception("An unexpected error occurred during email notification")
            raise NotificationError(f"Unexpected error sending email: {e}") from e

# --- Application Service ---

class ServerMonitor:
    """Orchestrates server checking and notification."""

    def __init__(self, checker: HttpChecker, notifier: Notifier, alert_codes: List[int]):
        self._checker = checker
        self._notifier = notifier
        self._alert_codes = set(alert_codes) # Use a set for faster lookups

    def run_check_and_notify(self, target: CheckTarget) -> None:
        """Runs the check and sends notification if an alert code is matched."""
        result = self._checker.check(target)

        if not result.success:
            # Optionally notify on check failures (timeouts, connection errors)
            # self._notify_failure(result)
            logger.warning(f"Check failed for {target.get_url()}: {result.error_message}")
            return # Don't proceed if the check itself failed

        if result.status_code is None:
             logger.warning(f"Check succeeded but no status code received for {target.get_url()}")
             return # Cannot compare status code if none exists


        if result.status_code in self._alert_codes:
            logger.warning(
                f"Alert triggered for {target.get_url()}: "
                f"Status code {result.status_code} matched target codes."
            )
            subject = f"🚨 Server Alert ({result.status_code}) on {target.host}"
            body = f"""
            An alert condition was detected on {target.get_url()}:

            **Status Code:** {result.status_code}
            **Timestamp:** {logging.Formatter().formatTime(logging.LogRecord(None, None, "", 0, "", (), None, None))}

            **Response Content Snippet:**
            ```
            { (result.content or "")[:MAX_ERROR_CONTENT_LENGTH] }
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

# --- Main Execution / Configuration Loading ---

def load_smtp_config_from_env() -> SmtpConfig:
    """Loads SMTP configuration securely from environment variables."""
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD") # In real-world use secrets management

    # Determine default sender address
    default_sender = f"servermonitor@{os.uname().nodename}" if username else "servermonitor@example.com"

    return SmtpConfig(
        server=os.getenv("SMTP_SERVER", DEFAULT_SMTP_SERVER),
        port=int(os.getenv("SMTP_PORT", DEFAULT_SMTP_PORT)),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"), # Default to True for security
        sender_address=os.getenv("SMTP_FROM", default_sender),
        username=username,
        password=password
    )

def main() -> None:
    """Parses arguments, sets up components, and runs the check."""
    parser = argparse.ArgumentParser(description="Monitor HTTP status codes on a server and notify via email.")
    parser.add_argument("--email", required=True, help="Destination email address for notifications")
    parser.add_argument("--host", required=True, help="Host address (e.g., example.com or IP) to check")
    parser.add_argument("--port", type=int, default=None, help="Port number (default: 80 for http, 443 for https)")
    parser.add_argument("--scheme", choices=['http', 'https'], default=None, help="Protocol scheme (default: http for port 80, https for 443/other)")
    parser.add_argument(
        "--codes", "--status-codes", # Allow both names
        type=int,
        nargs="+",
        default=[500, 502, 503, 504], # Default to common server error codes
        dest="alert_codes",
        help="HTTP status codes to trigger alerts (default: 500 502 503 504)",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})")

    args = parser.parse_args()

    # Determine scheme and port defaults if not provided
    port = args.port
    scheme = args.scheme
    if scheme is None:
        if port == 443:
            scheme = 'https'
        else:
            scheme = 'http' # Default to http if scheme unspecified and port isn't 443
    if port is None:
        port = 443 if scheme == 'https' else 80 # Default port based on final scheme

    # --- Dependency Setup ---
    try:
        check_target = CheckTarget(host=args.host, port=port, scheme=scheme)
        smtp_config = load_smtp_config_from_env()
        notification_details = NotificationDetails(recipient_email=args.email)

        http_checker = HttpChecker(timeout=args.timeout)
        email_notifier = EmailNotifier(smtp_config=smtp_config, details=notification_details)
        # If you had other notifiers (SlackNotifier, etc.), you could choose here

        monitor = ServerMonitor(
            checker=http_checker,
            notifier=email_notifier, # Inject the chosen notifier
            alert_codes=args.alert_codes
        )

        # --- Run the Monitor ---
        monitor.run_check_and_notify(check_target)
        logger.info("Monitoring check completed.")

    except NotificationError as e:
         # Catch configuration errors from SmtpConfig loading or initial setup
         logger.error(f"Configuration or setup error: {e}")
         # No specific exit code defined for this script, just log
    except Exception as e:
        # Catch-all for unexpected errors during setup or execution
        logger.exception("An unexpected error occurred in the main execution block.")
         # No specific exit code defined for this script, just log


if __name__ == "__main__":
    main()
