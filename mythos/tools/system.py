"""System tools: volume and brightness, wrapping mythos.system_control."""

from __future__ import annotations

from mythos import system_control
from mythos.tools.registry import tool

_LEVEL_PARAM = {"level": {"type": "integer", "description": "Percentage 0-100"}}
_STEP_PARAM = {"step": {"type": "integer", "description": "Percent step, default 10"}}


@tool(description="Increase system volume.", parameters=_STEP_PARAM, required=[])
def volume_up(step: int = 10) -> str:
    return system_control.volume_up(step)


@tool(description="Decrease system volume.", parameters=_STEP_PARAM, required=[])
def volume_down(step: int = 10) -> str:
    return system_control.volume_down(step)


@tool(description="Set system volume to an absolute percentage.", parameters=_LEVEL_PARAM)
def set_volume(level: int) -> str:
    return system_control.set_volume(level)


@tool(description="Mute the system audio.")
def mute() -> str:
    return system_control.mute_volume()


@tool(description="Unmute the system audio.")
def unmute() -> str:
    return system_control.unmute_volume()


@tool(description="Increase screen brightness.", parameters=_STEP_PARAM, required=[])
def brightness_up(step: int = 10) -> str:
    return system_control.brightness_up(step)


@tool(description="Decrease screen brightness.", parameters=_STEP_PARAM, required=[])
def brightness_down(step: int = 10) -> str:
    return system_control.brightness_down(step)


@tool(description="Set screen brightness to an absolute percentage.", parameters=_LEVEL_PARAM)
def set_brightness(level: int) -> str:
    return system_control.set_brightness(level)
