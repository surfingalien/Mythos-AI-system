"""Centralized configuration for Mythos.

Loads settings from a local `.env` file (via python-dotenv, when installed)
and exposes them through a single `Config` object. Falls back to safe
defaults so the assistant can still start if some keys are missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional; plain environment variables still work
    pass


def _get(key: str, default: str = "") -> str:
    """Fetch an env var, returning `default` if missing or empty."""
    val = os.getenv(key, default)
    return val if val else default


def _parse_contacts(raw: str) -> dict[str, str]:
    """Parse CONTACTS env var: "john:john@example.com, jane:jane@x.com"."""
    contacts: dict[str, str] = {}
    for pair in raw.split(","):
        if ":" in pair:
            name, addr = pair.split(":", 1)
            if name.strip() and addr.strip():
                contacts[name.strip().lower()] = addr.strip()
    return contacts


def _placeholder(value: str) -> bool:
    return not value or "your-" in value


@dataclass
class Config:
    # --- LLM ---
    openai_api_key: str = field(default_factory=lambda: _get("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _get("OPENAI_MODEL", "gpt-4o-mini"))

    # --- Info services ---
    weather_api_key: str = field(default_factory=lambda: _get("WEATHER_API_KEY"))
    news_api_key: str = field(default_factory=lambda: _get("NEWS_API_KEY"))
    news_country: str = field(default_factory=lambda: _get("NEWS_COUNTRY", "us"))

    # --- Email ---
    email_address: str = field(default_factory=lambda: _get("EMAIL_ADDRESS"))
    email_password: str = field(default_factory=lambda: _get("EMAIL_PASSWORD"))
    email_smtp_host: str = field(default_factory=lambda: _get("EMAIL_SMTP_HOST", "smtp.gmail.com"))
    email_smtp_port: int = field(
        default_factory=lambda: int(_get("EMAIL_SMTP_PORT", "465") or 465))

    # --- Assistant behavior ---
    assistant_name: str = field(default_factory=lambda: _get("ASSISTANT_NAME", "Mythos"))
    default_city: str = field(default_factory=lambda: _get("DEFAULT_CITY", "New York"))
    wake_word: str = field(default_factory=lambda: _get("WAKE_WORD", "mythos").lower())

    # --- Audio engines ---
    # tts: auto | edge | pyttsx3     stt: auto | whisper | google
    # wake: auto | openwakeword | google
    tts_engine: str = field(default_factory=lambda: _get("TTS_ENGINE", "auto").lower())
    tts_voice: str = field(default_factory=lambda: _get("TTS_VOICE", "en-US-GuyNeural"))
    stt_engine: str = field(default_factory=lambda: _get("STT_ENGINE", "auto").lower())
    whisper_model: str = field(default_factory=lambda: _get("WHISPER_MODEL", "base"))
    wake_engine: str = field(default_factory=lambda: _get("WAKE_ENGINE", "auto").lower())
    wake_threshold: float = field(
        default_factory=lambda: float(_get("WAKE_THRESHOLD", "0.5") or 0.5))
    # Path to a custom openWakeWord model (.onnx/.tflite). openWakeWord only
    # ships a pretrained model for "hey jarvis"; any other wake word needs a
    # custom model here, otherwise the speech-recognition fallback is used.
    wake_model_path: str = field(default_factory=lambda: _get("WAKE_MODEL_PATH"))

    # --- Spotify (optional) ---
    spotify_client_id: str = field(default_factory=lambda: _get("SPOTIFY_CLIENT_ID"))
    spotify_client_secret: str = field(default_factory=lambda: _get("SPOTIFY_CLIENT_SECRET"))
    spotify_redirect_uri: str = field(
        default_factory=lambda: _get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"))

    # --- Home Assistant (optional) ---
    hass_url: str = field(default_factory=lambda: _get("HASS_URL"))
    hass_token: str = field(default_factory=lambda: _get("HASS_TOKEN"))

    # --- Personal notes / memory ---
    notes_dir: str = field(default_factory=lambda: _get("NOTES_DIR"))
    memory_path: str = field(default_factory=lambda: _get("MEMORY_PATH", "mythos_memory.json"))

    # --- Web UI ---
    web_host: str = field(default_factory=lambda: _get("WEB_HOST", "127.0.0.1"))
    web_port: int = field(default_factory=lambda: int(_get("WEB_PORT", "8765") or 8765))

    # --- MCP (optional, experimental): path to a JSON file of stdio servers ---
    mcp_config_path: str = field(default_factory=lambda: _get("MCP_CONFIG", "mcp_servers.json"))

    # --- Contacts (name -> email). Set via CONTACTS env var, e.g.
    #     CONTACTS=john:john@example.com,boss:boss@company.com
    contacts: dict = field(
        default_factory=lambda: _parse_contacts(_get("CONTACTS")))

    # --- Convenience flags ---
    @property
    def has_openai(self) -> bool:
        return not _placeholder(self.openai_api_key)

    @property
    def has_weather(self) -> bool:
        return not _placeholder(self.weather_api_key)

    @property
    def has_news(self) -> bool:
        return not _placeholder(self.news_api_key)

    @property
    def has_email(self) -> bool:
        return not (_placeholder(self.email_address) or _placeholder(self.email_password))

    @property
    def has_spotify(self) -> bool:
        return not (_placeholder(self.spotify_client_id)
                    or _placeholder(self.spotify_client_secret))

    @property
    def has_hass(self) -> bool:
        return not (_placeholder(self.hass_url) or _placeholder(self.hass_token))


# Singleton config used throughout the app
config = Config()
