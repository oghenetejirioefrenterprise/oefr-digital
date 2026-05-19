"""Gmail SMTP wrapper for customer-facing transactional emails."""
import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "oghenetejiri@gmail.com"
FROM_HEADER = '"DataStructured" <oghenetejiri@gmail.com>'
REPLY_TO = "info@oefrenterprise.com"


def send_plain(to: str, subject: str, body: str) -> None:
    """Send a plain-text email via Gmail SMTP. Raises on failure."""
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD not set in environment")

    msg = EmailMessage()
    msg["From"] = FROM_HEADER
    msg["To"] = to
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, password)
        smtp.send_message(msg)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("usage: email_sender.py <to> <subject> <body>", file=sys.stderr)
        sys.exit(2)
    send_plain(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"Sent to {sys.argv[1]}")
