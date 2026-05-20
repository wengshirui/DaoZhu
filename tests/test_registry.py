"""Tests for the tool registry."""

import json
import pytest
from accobot.tools.registry import ToolRegistry, tool_error, tool_result


def test_register_and_get_entry():
    """Tool can be registered and retrieved."""
    reg = ToolRegistry()
    reg.register(
        name="test_tool",
        toolset="test",
        schema={"description": "A test tool", "parameters": {"type": "object", "properties": {}}},
        handler=lambda args, **kw: '{"ok": true}',
    )
    entry = reg.get_entry("test_tool")
    assert entry is not None
    assert entry.name == "test_tool"
    assert entry.toolset == "test"


def test_get_all_tool_names():
    """All registered tool names are returned sorted."""
    reg = ToolRegistry()
    reg.register(name="beta", toolset="t", schema={}, handler=lambda a, **k: "{}")
    reg.register(name="alpha", toolset="t", schema={}, handler=lambda a, **k: "{}")
    assert reg.get_all_tool_names() == ["alpha", "beta"]


def test_get_definitions_format():
    """Definitions follow OpenAI tool format."""
    reg = ToolRegistry()
    reg.register(
        name="my_tool",
        toolset="demo",
        schema={"description": "Demo", "parameters": {"type": "object", "properties": {}}},
        handler=lambda a, **k: "{}",
    )
    defs = reg.get_definitions()
    assert len(defs) == 1
    assert defs[0]["type"] == "function"
    assert defs[0]["function"]["name"] == "my_tool"


def test_get_definitions_respects_check_fn():
    """Tools with failing check_fn are excluded from definitions."""
    reg = ToolRegistry()
    reg.register(
        name="available",
        toolset="t",
        schema={"description": "ok", "parameters": {}},
        handler=lambda a, **k: "{}",
        check_fn=lambda: True,
    )
    reg.register(
        name="unavailable",
        toolset="t",
        schema={"description": "nope", "parameters": {}},
        handler=lambda a, **k: "{}",
        check_fn=lambda: False,
    )
    defs = reg.get_definitions()
    names = [d["function"]["name"] for d in defs]
    assert "available" in names
    assert "unavailable" not in names


def test_dispatch_success():
    """Dispatch calls the handler and returns its result."""
    reg = ToolRegistry()
    reg.register(
        name="echo",
        toolset="t",
        schema={},
        handler=lambda args, **kw: json.dumps({"echo": args.get("msg")}),
    )
    result = json.loads(reg.dispatch("echo", {"msg": "hello"}))
    assert result == {"echo": "hello"}


def test_dispatch_unknown_tool():
    """Dispatch returns error for unknown tool."""
    reg = ToolRegistry()
    result = json.loads(reg.dispatch("nonexistent", {}))
    assert "error" in result


def test_dispatch_handler_exception():
    """Dispatch catches handler exceptions and returns error JSON."""
    reg = ToolRegistry()
    reg.register(
        name="broken",
        toolset="t",
        schema={},
        handler=lambda a, **k: (_ for _ in ()).throw(ValueError("boom")),
    )
    result = json.loads(reg.dispatch("broken", {}))
    assert "error" in result
    assert "boom" in result["error"]


def test_tool_error_helper():
    """tool_error returns proper JSON."""
    result = json.loads(tool_error("something went wrong"))
    assert result == {"error": "something went wrong"}


def test_tool_error_with_extra():
    """tool_error supports extra fields."""
    result = json.loads(tool_error("bad", code=400))
    assert result == {"error": "bad", "code": 400}


def test_tool_result_with_kwargs():
    """tool_result with kwargs returns proper JSON."""
    result = json.loads(tool_result(success=True, count=5))
    assert result == {"success": True, "count": 5}


def test_tool_result_with_data():
    """tool_result with data dict returns it directly."""
    result = json.loads(tool_result({"key": "value"}))
    assert result == {"key": "value"}


def test_get_toolset_tools():
    """get_toolset_tools returns tools belonging to a specific toolset."""
    reg = ToolRegistry()
    reg.register(name="a1", toolset="alpha", schema={}, handler=lambda a, **k: "{}")
    reg.register(name="a2", toolset="alpha", schema={}, handler=lambda a, **k: "{}")
    reg.register(name="b1", toolset="beta", schema={}, handler=lambda a, **k: "{}")
    assert reg.get_toolset_tools("alpha") == ["a1", "a2"]
    assert reg.get_toolset_tools("beta") == ["b1"]
    assert reg.get_toolset_tools("gamma") == []
