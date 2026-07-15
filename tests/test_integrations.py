"""Tests for Home Assistant and email tools with network/SMTP mocked out."""

from jarvis.config import config
from jarvis.tools import comms, home_assistant


class _FakeResponse:
    def __init__(self, ok=True, status_code=200, payload=None):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload or {}
        self.text = "err"

    def json(self):
        return self._payload


def test_hass_call(monkeypatch):
    monkeypatch.setattr(config, "hass_url", "http://ha.local:8123/")
    monkeypatch.setattr(config, "hass_token", "tok")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, json=json, auth=headers["Authorization"])
        return _FakeResponse()

    monkeypatch.setattr(home_assistant.requests, "post", fake_post)
    result = home_assistant.home_assistant_call("light", "turn_on", "light.kitchen")
    assert "Done" in result
    assert captured["url"] == "http://ha.local:8123/api/services/light/turn_on"
    assert captured["json"] == {"entity_id": "light.kitchen"}
    assert captured["auth"] == "Bearer tok"


def test_hass_state(monkeypatch):
    monkeypatch.setattr(config, "hass_url", "http://ha.local:8123")
    monkeypatch.setattr(config, "hass_token", "tok")
    payload = {"state": "21.5",
               "attributes": {"unit_of_measurement": "°C",
                              "friendly_name": "Living Room"}}
    monkeypatch.setattr(home_assistant.requests, "get",
                        lambda *a, **k: _FakeResponse(payload=payload))
    assert home_assistant.home_assistant_state("sensor.temp") == "Living Room is 21.5 °C."


def test_send_email_resolves_contact(monkeypatch):
    monkeypatch.setattr(config, "contacts", {"john": "john@example.com"})
    sent = {}

    def fake_send(address, subject, body):
        sent.update(address=address, subject=subject, body=body)
        return f"Email sent to {address}."

    monkeypatch.setattr(comms.email_sender, "send_email", fake_send)
    result = comms.send_email("John", "Hi", "Hello there")
    assert sent["address"] == "john@example.com"
    assert "sent" in result


def test_send_email_unknown_contact(monkeypatch):
    monkeypatch.setattr(config, "contacts", {"john": "john@example.com"})
    result = comms.send_email("stranger", "Hi", "Hello")
    assert "don't have an address" in result
    assert "john" in result
