"""Offline fallback router.

When no LLM is configured, this maps a spoken command to a (tool, arguments)
pair using keyword rules. It returns the routing decision without executing
anything, which keeps it pure and easy to test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jarvis.config import config

_WORD_NUMBERS = {
    "zero": 0, "ten": 10, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100,
}


@dataclass
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)


def extract_number(text: str) -> int | None:
    """Pull the first integer (digits or common word forms) out of a command."""
    m = re.search(r"\b(\d{1,3})\b", text)
    if m:
        return int(m.group(1))
    for word, value in _WORD_NUMBERS.items():
        if re.search(rf"\b{word}\b", text):
            return value
    return None


def normalize_email(spoken: str) -> str:
    """Convert spoken email forms ('john at example dot com') to an address."""
    s = spoken.lower().strip()
    s = s.replace(" at ", "@").replace(" dot ", ".")
    s = s.replace(" underscore ", "_").replace(" dash ", "-")
    return s.replace(" ", "")


def route(query: str) -> ToolCall | None:
    """Map a command to a tool call. Returns None when nothing matches."""
    q = query.lower().strip()

    if "wikipedia" in q:
        topic = q.replace("wikipedia", "").replace("search", "").strip()
        return ToolCall("wikipedia_summary", {"topic": topic})

    if "google search" in q or "search for" in q:
        term = q.replace("google search", "").replace("search for", "").strip()
        return ToolCall("web_search", {"query": term})

    if "play" in q and ("music" in q or "song" in q or "youtube" in q):
        song = re.sub(r"\b(play|music|song|on youtube)\b", "", q).strip()
        return ToolCall("play_on_youtube", {"song": song})

    for browser in ("chrome", "edge", "firefox"):
        if f"open {browser}" in q:
            return ToolCall("open_browser", {"browser": browser})

    if "time" in q:
        return ToolCall("get_time")

    if "weather" in q:
        if " in " in q:
            city = q.split(" in ")[-1].strip()
        else:
            city = config.default_city
        return ToolCall("get_weather", {"city": city})

    if "news" in q or "headlines" in q:
        return ToolCall("get_news")

    # 'unmute' must be checked before 'mute' ("unmute" contains "mute")
    if "unmute" in q:
        return ToolCall("unmute")
    if "mute" in q:
        return ToolCall("mute")
    if "volume up" in q or "increase volume" in q or "louder" in q:
        return ToolCall("volume_up")
    if "volume down" in q or "decrease volume" in q or "quieter" in q:
        return ToolCall("volume_down")
    if "set volume" in q or ("volume" in q and extract_number(q) is not None):
        value = extract_number(q)
        if value is not None:
            return ToolCall("set_volume", {"level": value})

    if "brightness up" in q or "increase brightness" in q or "brighter" in q:
        return ToolCall("brightness_up")
    if "brightness down" in q or "decrease brightness" in q or "dimmer" in q:
        return ToolCall("brightness_down")
    if "set brightness" in q or ("brightness" in q and extract_number(q) is not None):
        value = extract_number(q)
        if value is not None:
            return ToolCall("set_brightness", {"level": value})

    if "contacts" in q:
        return ToolCall("list_contacts")

    return None
