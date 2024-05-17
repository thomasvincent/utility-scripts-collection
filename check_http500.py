#!/usr/bin/env python3

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import List, NoReturn

import requests
import argparse

# Logging configuration (same level, new format)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)  # Get logger for this module

# Constants (for clarity and maintainability)
DEFAULT_SMTP_SERVER = "localhost"
DEFAULT_SMTP_PORT = 25
DEFAULT_TIMEOUT = 10  # seconds
MAX_ERROR_CONTENT_LENGTH = 250  # Max characters to include in the email

def send_mail(email: str, host: str, status_code: int, error_message: str) -> None:
    """Sends an email notification about a server error."""
    
    # More descriptive subject and body
    subject = f"🚨 Server Error ({status_code}) on {host}"
    body = f"""
    There was a server error on {host}:

    **Status Code:** {status_code}
    **Error Details:**
    {error_message[:MAX_ERROR_CONTENT_LENGTH]}  
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_USER", "servermonitor@example.com")  # Default sender
    msg["To"] = email

    smtp_server = os.getenv("SMTP_SERVER", DEFAULT_SMTP_SERVER)
    smtp_port = int(os.getenv("SMTP_PORT", DEFAULT_SMTP_PORT))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()  # Add STARTTLS for security if supported
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.sendmail(msg["From"], [email], msg.as_string())
        logger.info("Notification email sent successfully.")
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPException) as e:
        logger.error(f"Failed to send email: {e}")

def check_server(host: str, port: int, email: str, status_codes: List[int]) -> None:
    """Checks a server for specified HTTP errors."""
    url = f"http{'s' if port == 443 else ''}://{host}:{port}/"

    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        if response.status_code in status_codes:
            send_mail(email, host, response.status_code, response.text)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking {url}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor HTTP errors on a server.")
    parser.add_argument("--email", required=True, help="Destination email address")
    parser.add_argument("--host", required=True, help="Host to check")
    parser.add_argument("--port", type=int, default=80, help="Port number (default: 80)")
    parser.add_argument(
        "--status-codes",
        type=int,
        nargs="+",
        default=[500],
        help="HTTP status codes to trigger alerts (default: 500)",
    )
    args = parser.parse_args()

    check_server(args.host, args.port, args.email, args.status_codes)
