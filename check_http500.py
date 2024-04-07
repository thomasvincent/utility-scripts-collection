#!/usr/bin/env python3

import sys
import argparse
import requests
from email.mime.text import MIMEText
import smtplib

def send_mail(email, host, error_message):
    msg = MIMEText(error_message)
    msg['Subject'] = f'Server failure at host {host}'
    msg['From'] = "root@localhost"
    msg['To'] = email

    try:
        with smtplib.SMTP('localhost') as smtp:
            smtp.sendmail("root@localhost", [email], msg.as_string())
            print('Message sent.')
    except Exception as e:
        print(f'Failed to send email: {e}')

def check_server(host, port, email):
    proto = "https://" if port == 443 else "http://"
    url = f"{proto}{host}:{port}/"

    try:
        response = requests.get(url)
        if response.status_code == 500:
            send_mail(email, host, 'HTTP 500: Server Error')
    except requests.exceptions.RequestException as e:
        print(f'Error contacting {url}: {e}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check HTTP 500 errors on a server.')
    parser.add_argument('--email', required=True, help='Destination email address')
    parser.add_argument('--host', required=True, help='Host to check')
    parser.add_argument('--port', type=int, default=80, help='Port number (default: 80)')
    
    args = parser.parse_args()

    check_server(args.host, args.port, args.email)
