"""Tests for the MCP Client system (REQ-017)."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from accobot.mcp.client import (
    _interpolate_env_vars,
    _sanitize_name,
    _build_safe_env,
    _convert_mcp_schema,
    load_mcp_config,
    get_mcp_status,
    register_server_tools,
)


# =========================================================================
# Config Loading
# =========================================================================

class TestInterpolateEnvVars:
    def test_simple_interpolation(self):
        with patch.dict(os.environ, {"MY_KEY": "secret123"}):
            result = _interpolate_env_vars({"token": "${MY_KEY}"})
            assert result["token"] == "secret123"

    def test_missing_var_returns_empty(self):
        # Ensure the var doesn't exist
        os.environ.pop("NONEXISTENT_VAR_XYZ", None)
        result = _interpolate_env_vars({"token": "${NONEXISTENT_VAR_XYZ}"})
        assert result["token"] == ""

    def test_nested_dict(self):
        with patch.dict(os.environ, {"DB_URL": "localhost:5432"}):
            result = _interpolate_env_vars({
                "env": {"DATABASE_URL": "${DB_URL}"},
                "name": "test",
            })
            assert result["env"]["DATABASE_URL"] == "localhost:5432"
            assert result["name"] == "test"

    def test_no_interpolation_needed(self):
        result = _interpolate_env_vars({"command": "npx", "args": ["-y", "server"]})
        assert result["command"] == "npx"

    def test_list_interpolation(self):
        with patch.dict(os.environ, {"DIR": "/tmp"}):
            result = _interpolate_env_vars({"args": ["--dir", "${DIR}"]})
            assert result["args"] == ["--dir", "/tmp"]


class TestSanitizeName:
    def test_simple_name(self):
        assert _sanitize_name("playwright") == "playwright"

    def test_hyphenated_name(self):
        assert _sanitize_name("my-server") == "my_server"

    def test_special_chars(self):
        assert _sanitize_name("server.v2@latest") == "server_v2_latest"


class TestBuildSafeEnv:
    def test_includes_safe_keys(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin", "HOME": "/home/user", "SECRET_KEY": "xxx"}, clear=True):
            env = _build_safe_env(None)
            assert "PATH" in env
            assert "HOME" in env
            assert "SECRET_KEY" not in env

    def test_user_env_overrides(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
            env = _build_safe_env({"MY_TOKEN": "abc123"})
            assert env["MY_TOKEN"] == "abc123"
            assert "PATH" in env


class TestLoadMcpConfig:
    def test_empty_config(self, tmp_path):
        """No mcp_servers in config returns empty dict."""
        with patch("accobot.config.load_config", return_value={"model": {}}):
            result = load_mcp_config()
            assert result == {}

    def test_with_servers(self):
        mock_config = {
            "mcp_servers": {
                "playwright": {
                    "command": "npx",
                    "args": ["@playwright/mcp@latest"],
                    "enabled": True,
                },
            },
        }
        with patch("accobot.config.load_config", return_value=mock_config):
            result = load_mcp_config()
            assert "playwright" in result
            assert result["playwright"]["command"] == "npx"


# =========================================================================
# Schema Conversion
# =========================================================================

class TestConvertMcpSchema:
    def test_basic_conversion(self):
        mock_tool = MagicMock()
        mock_tool.name = "navigate"
        mock_tool.description = "Navigate to a URL"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL"},
            },
            "required": ["url"],
        }

        schema = _convert_mcp_schema("playwright", mock_tool)
        assert schema["name"] == "mcp_playwright_navigate"
        assert schema["description"] == "Navigate to a URL"
        assert schema["parameters"]["properties"]["url"]["type"] == "string"

    def test_missing_schema(self):
        mock_tool = MagicMock()
        mock_tool.name = "simple_tool"
        mock_tool.description = "A simple tool"
        mock_tool.inputSchema = None

        schema = _convert_mcp_schema("server", mock_tool)
        assert schema["name"] == "mcp_server_simple_tool"
        assert schema["parameters"]["type"] == "object"
        assert schema["parameters"]["properties"] == {}

    def test_name_sanitization(self):
        mock_tool = MagicMock()
        mock_tool.name = "get-data.v2"
        mock_tool.description = "Get data"
        mock_tool.inputSchema = {"type": "object", "properties": {}}

        schema = _convert_mcp_schema("my-server", mock_tool)
        assert schema["name"] == "mcp_my_server_get_data_v2"


# =========================================================================
# Tool Registration
# =========================================================================

class TestRegisterServerTools:
    def test_registers_tools(self):
        from accobot.tools.registry import registry

        mock_tool = MagicMock()
        mock_tool.name = "test_action"
        mock_tool.description = "A test action"
        mock_tool.inputSchema = {"type": "object", "properties": {"x": {"type": "string"}}}

        server_info = {
            "name": "test_server",
            "tools": [mock_tool],
            "timeout": 30,
        }

        registered = register_server_tools("test_server", server_info)
        assert "mcp_test_server_test_action" in registered

        # Verify it's in the registry
        entry = registry.get_entry("mcp_test_server_test_action")
        assert entry is not None
        assert entry.toolset == "mcp-test_server"


# =========================================================================
# MCP Status
# =========================================================================

class TestGetMcpStatus:
    def test_no_config(self):
        with patch("accobot.mcp.client.load_mcp_config", return_value={}):
            status = get_mcp_status()
            assert status == []

    def test_with_config(self):
        mock_config = {
            "playwright": {"command": "npx", "args": [], "enabled": True},
            "disabled_server": {"command": "x", "enabled": False},
        }
        with patch("accobot.mcp.client.load_mcp_config", return_value=mock_config):
            status = get_mcp_status()
            assert len(status) == 2
            assert status[0]["name"] == "playwright"
            assert status[0]["transport"] == "stdio"
