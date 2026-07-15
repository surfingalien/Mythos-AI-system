"""Tests for the brain's streaming sentence splitter and fallback path."""

import asyncio

from jarvis.config import config
from jarvis.llm import Brain, split_sentences


def test_split_waits_for_sentence_end():
    complete, rest = split_sentences("Hello there, I am still typ")
    assert complete == []
    assert rest == "Hello there, I am still typ"


def test_split_extracts_complete_sentences():
    complete, rest = split_sentences("First one. Second one! And a third")
    assert complete == ["First one.", "Second one!"]
    assert rest == "And a third"


def test_split_handles_quotes_and_parens():
    complete, rest = split_sentences('He said "stop." Then he left. Fin')
    assert complete == ['He said "stop."', "Then he left."]
    assert rest == "Fin"


def test_split_no_false_positive_on_decimals():
    complete, rest = split_sentences("It costs 3.50 dollars")
    assert complete == []
    assert rest == "It costs 3.50 dollars"


def test_fallback_routes_known_command(monkeypatch):
    monkeypatch.setattr(config, "openai_api_key", "")
    brain = Brain(config)
    reply = asyncio.run(brain.respond("what time is it"))
    assert "It is" in reply


def test_fallback_message_for_unknown_command(monkeypatch):
    monkeypatch.setattr(config, "openai_api_key", "")
    brain = Brain(config)
    reply = asyncio.run(brain.respond("compose a haiku about rust"))
    assert "OpenAI key" in reply
