"""Tests for the offline fallback router — including the historical bugs."""

from jarvis.config import config
from jarvis.router import extract_number, normalize_email, route


def test_unmute_not_swallowed_by_mute():
    assert route("unmute the sound").name == "unmute"
    assert route("mute the sound").name == "mute"


def test_weather_city_with_in_substring():
    # Regression: split("in") used to truncate cities ending in "in"
    call = route("what's the weather in berlin")
    assert call.name == "get_weather"
    assert call.arguments["city"] == "berlin"


def test_weather_defaults_to_config_city():
    call = route("how's the weather")
    assert call.name == "get_weather"
    assert call.arguments["city"] == config.default_city


def test_browsers():
    assert route("open chrome").arguments["browser"] == "chrome"
    assert route("open edge").arguments["browser"] == "edge"
    assert route("open firefox").arguments["browser"] == "firefox"


def test_volume_and_brightness():
    assert route("volume up").name == "volume_up"
    assert route("make it louder").name == "volume_up"
    assert route("set volume to 40").arguments == {"level": 40}
    assert route("set volume to fifty").arguments == {"level": 50}
    assert route("brightness down").name == "brightness_down"
    assert route("set brightness to 80").arguments == {"level": 80}


def test_music_and_wikipedia_and_search():
    call = route("play music bohemian rhapsody")
    assert call.name == "play_on_youtube"
    assert "bohemian rhapsody" in call.arguments["song"]

    call = route("wikipedia alan turing")
    assert call.name == "wikipedia_summary"
    assert call.arguments["topic"] == "alan turing"

    call = route("google search best pizza dough")
    assert call.name == "web_search"


def test_time_and_news_and_contacts():
    assert route("what time is it").name == "get_time"
    assert route("give me the news").name == "get_news"
    assert route("list my contacts").name == "list_contacts"


def test_unmatched_returns_none():
    assert route("tell me a story about dragons") is None


def test_extract_number():
    assert extract_number("set volume to 55") == 55
    assert extract_number("set it to seventy percent") == 70
    assert extract_number("no numbers here") is None


def test_normalize_email():
    assert normalize_email("john at example dot com") == "john@example.com"
    assert normalize_email("Jane Underscore Doe at mail dot org") == "jane_doe@mail.org"
