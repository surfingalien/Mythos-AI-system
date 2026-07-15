"""Tool package: import all built-in tool modules so they self-register."""

# Importing these modules registers their tools as a side effect.
from mythos.tools import (  # noqa: E402,F401
    comms,
    home_assistant,
    info,
    media,
    memory_tools,
    notes,
    registry,
    spotify,
    system,
)
from mythos.tools.registry import Tool, dispatch, schemas, tool

__all__ = ["Tool", "dispatch", "registry", "schemas", "tool"]
