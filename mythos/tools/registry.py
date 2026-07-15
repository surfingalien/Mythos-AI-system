"""Tool registry.

Capabilities are plain functions registered with the @tool decorator. The
registry produces OpenAI-compatible JSON schemas for LLM tool-calling and
dispatches calls by name. Every tool returns a human-readable string so the
result can be spoken directly or summarized by the LLM.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, dict]
    required: list[str]
    func: Callable[..., str]
    enabled: Callable[[], bool] = field(default=lambda: True)

    def schema(self) -> dict:
        """OpenAI `tools` entry for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }


_REGISTRY: dict[str, Tool] = {}


def tool(description: str,
         parameters: dict[str, dict] | None = None,
         required: list[str] | None = None,
         name: str | None = None,
         enabled: Callable[[], bool] | None = None) -> Callable:
    """Register a function as an assistant capability."""
    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        tool_name = name or func.__name__
        _REGISTRY[tool_name] = Tool(
            name=tool_name,
            description=description,
            parameters=parameters or {},
            required=required if required is not None else list(parameters or {}),
            func=func,
            enabled=enabled or (lambda: True),
        )
        return func
    return decorator


def register(t: Tool) -> None:
    """Register a pre-built Tool (used by dynamic sources such as MCP)."""
    _REGISTRY[t.name] = t


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def all_tools(include_disabled: bool = False) -> list[Tool]:
    return [t for t in _REGISTRY.values() if include_disabled or t.enabled()]


def schemas() -> list[dict]:
    """Schemas for all currently-enabled tools (for the LLM `tools` param)."""
    return [t.schema() for t in all_tools()]


def dispatch(name: str, arguments: dict) -> str:
    """Execute a tool by name. Never raises — errors come back as text."""
    t = _REGISTRY.get(name)
    if t is None:
        return f"Unknown tool: {name}"
    if not t.enabled():
        return f"The {name} capability isn't configured or available right now."
    try:
        result = t.func(**arguments)
        return result if isinstance(result, str) else str(result)
    except TypeError as e:
        return f"Invalid arguments for {name}: {e}"
    except Exception as e:
        return f"{name} failed: {e}"
