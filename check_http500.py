#!/usr/bin/env python3

import sys
import argparse
import requests
import smtplib
import os
import logging
from email.mime.text import MIMEText
from typing import NoReturn

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)


def send_mail(email: str, host: str, status_code: int, error_message: str) -> NoReturn:
    """Sends an email notification about a server error.

    Args:
        email: Destination email address.
        host: The host that experienced the error.
        status_code: The HTTP status code that triggered the alert.
        error_message: Additional details about the error.
    """
    msg = MIMEText(
        f"Server Error ({status_code}) at host {host}\n\nAdditional Details:\n{error_message}"
    )
    msg["Subject"] = f"Server Error ({status_code}) at host {host}"
    msg["From"] = "root@localhost"
    msg["To"] = email

    smtp_server = os.getenv("SMTP_SERVER", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", 25))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.sendmail("root@localhost", [email], msg.as_string())
            logging.info("Message sent.")
    except Exception as e:  # Log any SMTP errors
        logging.error(f"Failed to send email: {e}")


def check_server(host: str, port: int, email: str, status_codes: list[int]) -> NoReturn:
    """Checks a server for specified HTTP errors and sends notifications.

    Args:
        host: The host to check.
        port: The port number.
        email: Destination email address.
        status_codes: A list of HTTP status codes to trigger alerts.
    """
    proto = "https://" if port == 443 else "http://"
    url = f"{proto}{host}:{port}/"
    timeout = 10  # seconds

    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code in status_codes:
            send_mail(email, host, response.status_code, response.text[:250])  # Truncate long responses 
    except requests.exceptions.Timeout as e:
        logging.error(f"Connection to {url} timed out: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error contacting {url}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check HTTP errors on a server.")
    parser.add_argument("--email", required=True, help="Destination email address")
    parser.add_argument("--host", required=True, help="Host to check")
    parser.add_argument(
        "--port", type=int, default=80, help="Port number (default: 80)"
    )
    parser.add_argument(
        "--status-codes",
        type=int,
        nargs="+",  # Allow multiple status codes
        default=[500],
        help="HTTP status codes to trigger alerts (default: 500)",
    )

    args = parser.parse_args()

    check_server(args.host, args.port, args.email, args.status_codes)
