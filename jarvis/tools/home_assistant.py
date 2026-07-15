"""Home Assistant tools (optional): control smart-home devices via the REST API.

Requires HASS_URL (e.g. http://homeassistant.local:8123) and a long-lived
access token in HASS_TOKEN.
"""

from __future__ import annotations

import requests

from jarvis.config import config
from jarvis.tools.registry import tool


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.hass_token}",
        "Content-Type": "application/json",
    }


def _base() -> str:
    return config.hass_url.rstrip("/")


@tool(
    description="Call a Home Assistant service to control a device, e.g. "
                "domain='light', service='turn_on', entity_id='light.living_room'.",
    parameters={
        "domain": {"type": "string", "description": "Service domain, e.g. 'light', 'switch'"},
        "service": {"type": "string",
                    "description": "Service name, e.g. 'turn_on', 'turn_off', 'toggle'"},
        "entity_id": {"type": "string", "description": "Target entity, e.g. 'light.kitchen'"},
    },
    enabled=lambda: config.has_hass,
)
def home_assistant_call(domain: str, service: str, entity_id: str) -> str:
    resp = requests.post(
        f"{_base()}/api/services/{domain}/{service}",
        headers=_headers(),
        json={"entity_id": entity_id},
        timeout=10,
    )
    if resp.ok:
        return f"Done — {service} sent to {entity_id}."
    return f"Home Assistant returned {resp.status_code}: {resp.text[:200]}"


@tool(
    description="Get the current state of a Home Assistant entity "
                "(e.g. is a light on, a sensor's temperature).",
    parameters={"entity_id": {"type": "string", "description": "Entity, e.g. 'light.kitchen'"}},
    enabled=lambda: config.has_hass,
)
def home_assistant_state(entity_id: str) -> str:
    resp = requests.get(f"{_base()}/api/states/{entity_id}", headers=_headers(), timeout=10)
    if not resp.ok:
        return f"Couldn't read {entity_id}: HTTP {resp.status_code}."
    data = resp.json()
    state = data.get("state", "unknown")
    unit = data.get("attributes", {}).get("unit_of_measurement", "")
    name = data.get("attributes", {}).get("friendly_name", entity_id)
    return f"{name} is {state}{(' ' + unit) if unit else ''}."
