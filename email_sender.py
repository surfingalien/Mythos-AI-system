"""
email_sender.py
Send emails via SMTP using credentials from config.

Supports:
  - Direct address:   send_email("someone@example.com", "Hello", "Body")
  - Contact lookup:   send_email_to_contact("john", "Hello", "Body")
    (looks up "john" in config.contacts)
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import config


def send_email(to_address: str, subject: str, body: str) -> str:
    """Send a plain-text email. Returns a status string for speak()."""
    if not config.has_email:
        return ("Email is not configured, sir. "
                "Please set EMAIL_ADDRESS and EMAIL_PASSWORD in your .env file.")

    try:
        msg = MIMEMultipart()
        msg["From"] = config.email_address
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Port 465 -> SSL; 587 -> STARTTLS. Anything else -> try STARTTLS.
        if config.email_smtp_port == 465:
            with smtplib.SMTP_SSL(config.email_smtp_host,
                                  config.email_smtp_port,
                                  timeout=20) as server:
                server.login(config.email_address, config.email_password)
                server.sendmail(config.email_address, to_address, msg.as_string())
        else:
            with smtplib.SMTP(config.email_smtp_host,
                              config.email_smtp_port,
                              timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config.email_address, config.email_password)
                server.sendmail(config.email_address, to_address, msg.as_string())

        return f"Email sent to {to_address}."
    except smtplib.SMTPAuthenticationError:
        return ("Authentication failed, sir. For Gmail, you need an App Password, "
                "not your regular password.")
    except Exception as e:
        return f"I couldn't send the email: {e}"


def send_email_to_contact(name: str, subject: str, body: str) -> str:
    """Look up a contact by name (case-insensitive) and send."""
    key = name.lower().strip()
    address = config.contacts.get(key)
    if not address:
        known = ", ".join(config.contacts.keys()) or "none"
        return (f"I don't have a contact named {name} in my address book, sir. "
                f"Known contacts: {known}.")
    return send_email(address, subject, body)


def list_contacts() -> str:
    if not config.contacts:
        return "Your address book is empty, sir."
    names = ", ".join(config.contacts.keys())
    return f"Your contacts are: {names}."
