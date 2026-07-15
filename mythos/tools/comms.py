"""Communication tools: email sending and contact lookup."""

from __future__ import annotations

from mythos import email_sender
from mythos.config import config
from mythos.tools.registry import tool


@tool(
    description="Send an email. 'to' may be a full address or a saved contact name. "
                "Ask the user for any missing field before calling this.",
    parameters={
        "to": {"type": "string", "description": "Recipient address or contact name"},
        "subject": {"type": "string", "description": "Email subject"},
        "body": {"type": "string", "description": "Email body text"},
    },
    enabled=lambda: config.has_email,
)
def send_email(to: str, subject: str, body: str) -> str:
    address = config.contacts.get(to.lower().strip(), to.strip())
    if "@" not in address:
        known = ", ".join(config.contacts) or "none"
        return (f"I don't have an address for {to}. "
                f"Known contacts: {known}. Please give me a full email address.")
    return email_sender.send_email(address, subject, body)


@tool(description="List the user's saved email contacts.")
def list_contacts() -> str:
    return email_sender.list_contacts()
