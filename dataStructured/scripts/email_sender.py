#!/usr/bin/env python3
"""Gmail SMTP email sender for DataStructured customer emails.

Thin wrapper around smtplib for transactional email.
Credentials from environment: GMAIL_APP_PASSWORD.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
# Fallback sender address if GMAIL_ADDRESS is not set in the environment.
DEFAULT_SENDER_EMAIL = "oghenetejiri@gmail.com"
SENDER_DISPLAY = "DataStructured"
REPLY_TO = "info@oefrenterprise.com"


def send_email(to: str, subject: str, body_text: str, body_html: str | None = None) -> None:
    """Send an email via Gmail SMTP.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body_text: Plain text body.
        body_html: Optional HTML body. If provided, sends multipart.

    Raises:
        smtplib.SMTPException: On any SMTP failure (caller should NOT mark email as sent).
        EnvironmentError: If GMAIL_APP_PASSWORD is not set.
    """
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise EnvironmentError("GMAIL_APP_PASSWORD not set in environment")

    # Resolve the sender/login address from env (falls back to the default) so
    # the SMTP login account and the From header always match the credential.
    sender_email = os.environ.get("GMAIL_ADDRESS", DEFAULT_SENDER_EMAIL)

    if body_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
    else:
        msg = MIMEText(body_text, "plain")

    msg["From"] = f"{SENDER_DISPLAY} <{sender_email}>"
    msg["To"] = to
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = subject

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, [to], msg.as_string())
