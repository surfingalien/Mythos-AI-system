"""Experimental MCP client: expose external MCP server tools to the brain.

Configure servers in mcp_servers.json (path via MCP_CONFIG):

    {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/me"]
      }
    }

Each server's tools are registered into the Mythos tool registry as
"<server>__<tool>", so the LLM can call them like any built-in capability.
Requires the official `mcp` Python package.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import AsyncExitStack
from pathlib import Path

from mythos.tools import registry

_stack: AsyncExitStack | None = None
_loop: asyncio.AbstractEventLoop | None = None


async def connect_all(config_path: str | Path) -> int:
    """Connect to every configured server and register its tools.

    Returns the number of tools registered. Must be called from the event
    loop that will keep running for the lifetime of the assistant.
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    global _stack, _loop
    _loop = asyncio.get_running_loop()
    _stack = AsyncExitStack()

    servers = json.loads(Path(config_path).read_text(encoding="utf-8"))
    registered = 0
    for server_name, spec in servers.items():
        params = StdioServerParameters(
            command=spec["command"],
            args=spec.get("args", []),
            env=spec.get("env"),
        )
        read, write = await _stack.enter_async_context(stdio_client(params))
        session = await _stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        tools_result = await session.list_tools()
        for t in tools_result.tools:
            _register_remote_tool(server_name, session, t)
            registered += 1
    return registered


def _register_remote_tool(server_name: str, session, t) -> None:
    full_name = f"{server_name}__{t.name}"
    input_schema = t.inputSchema or {}

    def call_remote(**kwargs) -> str:
        # Tools are dispatched from worker threads; hop back onto the loop
        # that owns the MCP session.
        future = asyncio.run_coroutine_threadsafe(
            session.call_tool(t.name, kwargs), _loop)
        result = future.result(timeout=60)
        parts = []
        for item in result.content:
            text = getattr(item, "text", None)
            parts.append(text if text is not None else str(item))
        return "\n".join(parts) or "(no output)"

    registry.register(registry.Tool(
        name=full_name,
        description=t.description or f"{t.name} (from MCP server {server_name})",
        parameters=input_schema.get("properties", {}),
        required=input_schema.get("required", []),
        func=call_remote,
    ))


async def close() -> None:
    global _stack
    if _stack is not None:
        await _stack.aclose()
        _stack = None
