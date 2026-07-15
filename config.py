"""
config.py
Centralized configuration loader for Jarvis.

Loads settings from a local `.env` file (via python-dotenv) and exposes
them through a single `Config` object. Falls back to safe defaults so
the assistant can still start if some keys are missing.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load variables from .env (if present) into os.environ
load_dotenv()


def _get(key: str, default: str = "") -> str:
    """Fetch an env var, returning `default` if missing or empty."""
    val = os.getenv(key, default)
    return val if val else default


@dataclass
class Config:
    # --- API keys ---
    openai_api_key: str = field(default_factory=lambda: _get("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _get("OPENAI_MODEL", "gpt-3.5-turbo"))

    weather_api_key: str = field(default_factory=lambda: _get("WEATHER_API_KEY"))
    news_api_key: str = field(default_factory=lambda: _get("NEWS_API_KEY"))
    news_country: str = field(default_factory=lambda: _get("NEWS_COUNTRY", "us"))

    # --- Email ---
    email_address: str = field(default_factory=lambda: _get("EMAIL_ADDRESS"))
    email_password: str = field(default_factory=lambda: _get("EMAIL_PASSWORD"))
    email_smtp_host: str = field(default_factory=lambda: _get("EMAIL_SMTP_HOST", "smtp.gmail.com"))
    email_smtp_port: int = field(default_factory=lambda: int(_get("EMAIL_SMTP_PORT", "465") or 465))

    # --- Assistant behavior ---
    assistant_name: str = field(default_factory=lambda: _get("ASSISTANT_NAME", "Jarvis"))
    default_city: str = field(default_factory=lambda: _get("DEFAULT_CITY", "New York"))
    wake_word: str = field(default_factory=lambda: _get("WAKE_WORD", "jarvis").lower())

    # --- Contacts (name -> email) for the "send email to <name>" command ---
    # Edit this dict to add your own contacts. Names should be lowercase.
    contacts: dict = field(default_factory=lambda: {
        "john": "john@example.com",
        "jane": "jane@example.com",
        "boss": "boss@company.com",
    })

    # --- Convenience flags ---
    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key) and "your-" not in self.openai_api_key

    @property
    def has_weather(self) -> bool:
        return bool(self.weather_api_key) and "your-" not in self.weather_api_key

    @property
    def has_news(self) -> bool:
        return bool(self.news_api_key) and "your-" not in self.news_api_key

    @property
    def has_email(self) -> bool:
        return (bool(self.email_address)
                and bool(self.email_password)
                and "your-" not in self.email_address
                and "your-" not in self.email_password)


# Singleton config used throughout the app
config = Config()
