"""Tests for configuration parsing."""

from mythos.config import _parse_contacts, _placeholder


def test_parse_contacts():
    contacts = _parse_contacts("john:john@example.com, Boss : boss@co.com")
    assert contacts == {"john": "john@example.com", "boss": "boss@co.com"}


def test_parse_contacts_empty_and_malformed():
    assert _parse_contacts("") == {}
    assert _parse_contacts("no-colon-here") == {}
    assert _parse_contacts(":missing@name.com,name:") == {}


def test_placeholder_detection():
    assert _placeholder("")
    assert _placeholder("your-openai-api-key-here")
    assert not _placeholder("sk-real-key-123")
