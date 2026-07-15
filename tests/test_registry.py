"""Tests for the tool registry: schemas, dispatch, enable gating."""

from jarvis.tools import registry
from jarvis.tools.registry import dispatch, tool


def test_schema_shape():
    t = registry.get("get_time")
    assert t is not None
    schema = t.schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "get_time"
    assert schema["function"]["parameters"]["type"] == "object"


def test_dispatch_executes_tool():
    @tool(description="test echo",
          parameters={"text": {"type": "string"}},
          name="_test_echo")
    def echo(text: str) -> str:
        return f"echo:{text}"

    assert dispatch("_test_echo", {"text": "hi"}) == "echo:hi"


def test_dispatch_unknown_tool():
    assert "Unknown tool" in dispatch("no_such_tool", {})


def test_dispatch_disabled_tool():
    @tool(description="always off", name="_test_disabled", enabled=lambda: False)
    def disabled() -> str:
        return "should never run"

    result = dispatch("_test_disabled", {})
    assert "isn't configured" in result


def test_dispatch_bad_arguments():
    @tool(description="needs arg",
          parameters={"x": {"type": "string"}},
          name="_test_needs_arg")
    def needs_arg(x: str) -> str:
        return x

    assert "Invalid arguments" in dispatch("_test_needs_arg", {"wrong": "1"})


def test_dispatch_never_raises():
    @tool(description="boom", name="_test_boom")
    def boom() -> str:
        raise RuntimeError("kaput")

    assert "kaput" in dispatch("_test_boom", {})


def test_disabled_tools_excluded_from_schemas():
    names = [s["function"]["name"] for s in registry.schemas()]
    assert "_test_disabled" not in names
    assert "get_time" in names
