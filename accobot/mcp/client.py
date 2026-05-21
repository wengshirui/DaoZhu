"""MCP Client — connect to MCP servers, discover tools, register them.

Simplified from Hermes Agent's tools/mcp_tool.py (~3400 lines → ~300 lines).
Keeps the essential architecture: background event loop, stdio/HTTP transport,
tool discovery, and transparent registry integration.

Usage:
    from accobot.mcp.client import discover_mcp_tools
    tool_names = discover_mcp_tools()  # reads config, connects, registers
"""

import asyncio
import json
import logging
import os
import re
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check if MCP SDK is available
_MCP_AVAILABLE = False
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    _MCP_AVAILABLE = True
except ImportError:
    pass

_MCP_HTTP_AVAILABLE = False
try:
    from mcp.client.streamable_http import streamablehttp_client
    _MCP_HTTP_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TOOL_TIMEOUT = 120      # seconds per tool call
_DEFAULT_CONNECT_TIMEOUT = 30    # seconds for initial connection
_MAX_RETRIES = 3
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Safe env vars to pass to stdio subprocesses
_SAFE_ENV_KEYS = frozenset({
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM", "SHELL", "TMPDIR",
    "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT",  # Windows
})

# ---------------------------------------------------------------------------
# Module State
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_mcp_loop: Optional[asyncio.AbstractEventLoop] = None
_mcp_thread: Optional[threading.Thread] = None
_servers: Dict[str, Any] = {}  # name → session info
_registered_tools: Dict[str, str] = {}  # tool_name → server_name


# ---------------------------------------------------------------------------
# Config Loading
# ---------------------------------------------------------------------------

def _interpolate_env_vars(config: dict) -> dict:
    """Resolve ${VAR_NAME} placeholders in config values."""
    result = {}
    for key, value in config.items():
        if isinstance(value, str):
            def _replace(m):
                var_name = m.group(1)
                val = os.environ.get(var_name, "")
                if not val:
                    logger.warning("MCP config: env var ${%s} not set", var_name)
                return val
            result[key] = _ENV_VAR_PATTERN.sub(_replace, value)
        elif isinstance(value, dict):
            result[key] = _interpolate_env_vars(value)
        elif isinstance(value, list):
            result[key] = [
                _ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), str(v))
                if isinstance(v, str) else v
                for v in value
            ]
        else:
            result[key] = value
    return result


def load_mcp_config() -> Dict[str, dict]:
    """Load MCP server configuration from AccoBot config.yaml.

    Returns {server_name: server_config} dict.
    """
    from accobot.config import load_config, load_env
    load_env()  # Ensure .env vars available for interpolation

    config = load_config()
    servers = config.get("mcp_servers")
    if not servers or not isinstance(servers, dict):
        return {}

    return {name: _interpolate_env_vars(cfg) for name, cfg in servers.items()}


# ---------------------------------------------------------------------------
# Background Event Loop
# ---------------------------------------------------------------------------

def _ensure_mcp_loop():
    """Start the background asyncio event loop for MCP connections."""
    global _mcp_loop, _mcp_thread

    if _mcp_loop is not None and _mcp_loop.is_running():
        return

    _mcp_loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(_mcp_loop)
        _mcp_loop.run_forever()

    _mcp_thread = threading.Thread(target=_run, daemon=True, name="mcp-loop")
    _mcp_thread.start()


def _run_on_mcp_loop(coro, timeout: float = 60) -> Any:
    """Schedule a coroutine on the MCP loop and wait for result."""
    _ensure_mcp_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _mcp_loop)
    return future.result(timeout=timeout)


# ---------------------------------------------------------------------------
# Server Connection
# ---------------------------------------------------------------------------

def _build_safe_env(user_env: Optional[dict]) -> dict:
    """Build filtered environment for stdio subprocesses."""
    env = {}
    for key, value in os.environ.items():
        if key in _SAFE_ENV_KEYS or key.startswith("XDG_"):
            env[key] = value
    if user_env:
        env.update(user_env)
    return env


def _sanitize_name(name: str) -> str:
    """Convert server/tool name to a valid Python identifier component."""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(name))


async def _connect_stdio(name: str, config: dict) -> Optional[Dict[str, Any]]:
    """Connect to a stdio MCP server and discover its tools.

    Uses a persistent background task to keep the connection alive.
    The session remains valid as long as the task is running.
    """
    command = config.get("command", "")
    args = config.get("args", [])
    env = _build_safe_env(config.get("env"))
    timeout = config.get("timeout", _DEFAULT_TOOL_TIMEOUT)

    if not command:
        logger.error("MCP server '%s': no command specified", name)
        return None

    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=env,
    )

    # We need to keep the context managers alive. Use an Event to signal
    # when initialization is complete, and a Future to hold the result.
    init_event = asyncio.Event()
    server_info_holder: Dict[str, Any] = {}
    error_holder: List[Optional[Exception]] = [None]

    async def _run_server():
        """Long-lived task that keeps the stdio connection open."""
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # Discover tools
                    tools_result = await session.list_tools()
                    tools = tools_result.tools if hasattr(tools_result, 'tools') else []

                    server_info_holder.update({
                        "name": name,
                        "session": session,
                        "tools": tools,
                        "timeout": timeout,
                        "transport": "stdio",
                    })
                    init_event.set()

                    # Keep alive until cancelled
                    try:
                        while True:
                            await asyncio.sleep(60)
                    except asyncio.CancelledError:
                        logger.info("MCP server '%s' task cancelled", name)
        except Exception as e:
            error_holder[0] = e
            init_event.set()

    # Start the persistent task
    task = asyncio.ensure_future(_run_server())

    # Wait for initialization
    try:
        await asyncio.wait_for(init_event.wait(), timeout=config.get("connect_timeout", _DEFAULT_CONNECT_TIMEOUT))
    except asyncio.TimeoutError:
        task.cancel()
        logger.error("MCP server '%s': connection timed out", name)
        return None

    if error_holder[0]:
        logger.error("MCP server '%s' connection failed: %s", name, error_holder[0])
        return None

    server_info_holder["_task"] = task
    return server_info_holder


async def _connect_http(name: str, config: dict) -> Optional[Dict[str, Any]]:
    """Connect to an HTTP MCP server and discover its tools.

    Uses a persistent background task to keep the connection alive.
    """
    if not _MCP_HTTP_AVAILABLE:
        logger.error("MCP HTTP transport not available (install mcp[http])")
        return None

    url = config.get("url", "")
    timeout = config.get("timeout", _DEFAULT_TOOL_TIMEOUT)
    headers = config.get("headers", {})

    if not url:
        logger.error("MCP server '%s': no url specified", name)
        return None

    init_event = asyncio.Event()
    server_info_holder: Dict[str, Any] = {}
    error_holder: List[Optional[Exception]] = [None]

    async def _run_server():
        try:
            async with streamablehttp_client(url, headers=headers) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    tools = tools_result.tools if hasattr(tools_result, 'tools') else []

                    server_info_holder.update({
                        "name": name,
                        "session": session,
                        "tools": tools,
                        "timeout": timeout,
                        "transport": "http",
                    })
                    init_event.set()

                    try:
                        while True:
                            await asyncio.sleep(60)
                    except asyncio.CancelledError:
                        logger.info("MCP server '%s' HTTP task cancelled", name)
        except Exception as e:
            error_holder[0] = e
            init_event.set()

    task = asyncio.ensure_future(_run_server())

    try:
        await asyncio.wait_for(init_event.wait(), timeout=config.get("connect_timeout", _DEFAULT_CONNECT_TIMEOUT))
    except asyncio.TimeoutError:
        task.cancel()
        logger.error("MCP server '%s': HTTP connection timed out", name)
        return None

    if error_holder[0]:
        logger.error("MCP server '%s' HTTP connection failed: %s", name, error_holder[0])
        return None

    server_info_holder["_task"] = task
    return server_info_holder


# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------

def _convert_mcp_schema(server_name: str, mcp_tool) -> dict:
    """Convert an MCP tool to AccoBot registry schema format."""
    safe_server = _sanitize_name(server_name)
    safe_tool = _sanitize_name(mcp_tool.name)
    prefixed_name = f"mcp_{safe_server}_{safe_tool}"

    # Normalize input schema
    input_schema = getattr(mcp_tool, "inputSchema", None) or {}
    if not isinstance(input_schema, dict):
        input_schema = {"type": "object", "properties": {}}
    if "type" not in input_schema:
        input_schema["type"] = "object"
    if "properties" not in input_schema:
        input_schema["properties"] = {}

    return {
        "name": prefixed_name,
        "description": mcp_tool.description or f"MCP tool {mcp_tool.name} from {server_name}",
        "parameters": input_schema,
    }


def _make_tool_handler(server_name: str, tool_name: str, timeout: int):
    """Create a handler function for an MCP tool."""
    def handler(args: dict, **kwargs) -> str:
        try:
            result = _call_mcp_tool(server_name, tool_name, args, timeout)
            return result
        except Exception as e:
            return json.dumps({"error": f"MCP tool call failed: {e}"}, ensure_ascii=False)
    return handler


def _call_mcp_tool(server_name: str, tool_name: str, args: dict, timeout: int) -> str:
    """Call an MCP tool via the background event loop."""
    with _lock:
        server_info = _servers.get(server_name)
    if not server_info:
        return json.dumps({"error": f"MCP server '{server_name}' not connected"}, ensure_ascii=False)

    session = server_info["session"]

    async def _call():
        result = await asyncio.wait_for(
            session.call_tool(tool_name, args),
            timeout=timeout,
        )
        # Extract text content from result
        if hasattr(result, 'content') and result.content:
            parts = []
            for block in result.content:
                if hasattr(block, 'text'):
                    parts.append(block.text)
            return "\n".join(parts) if parts else json.dumps({"success": True})
        return json.dumps({"success": True, "result": str(result)})

    return _run_on_mcp_loop(_call(), timeout=timeout + 5)


def register_server_tools(name: str, server_info: dict) -> List[str]:
    """Register all tools from a connected MCP server into AccoBot's registry."""
    from accobot.tools.registry import registry

    registered = []
    toolset_name = f"mcp-{name}"
    timeout = server_info.get("timeout", _DEFAULT_TOOL_TIMEOUT)

    for mcp_tool in server_info.get("tools", []):
        schema = _convert_mcp_schema(name, mcp_tool)
        tool_name_prefixed = schema["name"]

        # Skip if already registered (idempotent)
        if registry.get_entry(tool_name_prefixed):
            registered.append(tool_name_prefixed)
            continue

        registry.register(
            name=tool_name_prefixed,
            toolset=toolset_name,
            schema=schema,
            handler=_make_tool_handler(name, mcp_tool.name, timeout),
            emoji="🔌",
        )
        registered.append(tool_name_prefixed)

    with _lock:
        for t in registered:
            _registered_tools[t] = name

    return registered


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_mcp_tools() -> List[str]:
    """Main entry point: load config, connect to servers, register tools.

    Safe to call even when MCP SDK is not installed (returns empty list).
    Idempotent for already-connected servers.
    Retries failed connections up to _MAX_RETRIES times with exponential backoff.
    """
    if not _MCP_AVAILABLE:
        logger.debug("MCP SDK not installed — skipping MCP tool discovery")
        return []

    servers_config = load_mcp_config()
    if not servers_config:
        return []

    all_tool_names = []

    for name, config in servers_config.items():
        # Skip disabled servers
        enabled = config.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.lower() in ("true", "1", "yes")
        if not enabled:
            continue

        # Skip already connected
        with _lock:
            if name in _servers:
                existing = [t for t, s in _registered_tools.items() if s == name]
                all_tool_names.extend(existing)
                continue

        # Connect with retry
        server_info = None
        connect_timeout = config.get("connect_timeout", _DEFAULT_CONNECT_TIMEOUT)

        for attempt in range(_MAX_RETRIES):
            try:
                if "url" in config:
                    server_info = _run_on_mcp_loop(
                        _connect_http(name, config),
                        timeout=connect_timeout + 5,
                    )
                else:
                    server_info = _run_on_mcp_loop(
                        _connect_stdio(name, config),
                        timeout=connect_timeout + 5,
                    )
                if server_info:
                    break
            except Exception as e:
                wait = 2 ** attempt  # 1s, 2s, 4s
                if attempt < _MAX_RETRIES - 1:
                    logger.info(
                        "MCP server '%s' attempt %d failed (%s), retrying in %ds...",
                        name, attempt + 1, e, wait,
                    )
                    import time
                    time.sleep(wait)
                else:
                    logger.warning("MCP server '%s' failed after %d attempts: %s", name, _MAX_RETRIES, e)

        if not server_info:
            continue

        # Store and register
        with _lock:
            _servers[name] = server_info

        registered = register_server_tools(name, server_info)
        all_tool_names.extend(registered)

        logger.info(
            "MCP server '%s' (%s): registered %d tool(s)",
            name, server_info.get("transport", "?"), len(registered),
        )

    return all_tool_names


def get_mcp_status() -> List[Dict[str, Any]]:
    """Return status of all configured MCP servers (for Web UI)."""
    servers_config = load_mcp_config()
    status = []

    for name, config in servers_config.items():
        with _lock:
            connected = name in _servers
            tool_count = len([t for t, s in _registered_tools.items() if s == name])

        status.append({
            "name": name,
            "connected": connected,
            "tool_count": tool_count,
            "transport": "http" if "url" in config else "stdio",
            "enabled": config.get("enabled", True),
        })

    return status


def shutdown_mcp():
    """Shutdown all MCP connections and stop the background loop.

    Cancels all persistent server tasks and cleans up resources.
    Called on AccoBot exit to prevent orphan processes.
    """
    global _mcp_loop, _mcp_thread

    # Cancel all server tasks
    with _lock:
        for name, info in _servers.items():
            task = info.get("_task")
            if task and not task.done():
                _mcp_loop.call_soon_threadsafe(task.cancel)
                logger.debug("Cancelled MCP server task: %s", name)
        _servers.clear()
        _registered_tools.clear()

    # Stop the event loop
    if _mcp_loop and _mcp_loop.is_running():
        _mcp_loop.call_soon_threadsafe(_mcp_loop.stop)

    if _mcp_thread and _mcp_thread.is_alive():
        _mcp_thread.join(timeout=5)

    _mcp_loop = None
    _mcp_thread = None
    logger.debug("MCP shutdown complete")


def reconnect_server(name: str) -> bool:
    """Reconnect a specific MCP server (for Web UI reconnect button).

    Returns True if reconnection succeeded.
    """
    if not _MCP_AVAILABLE:
        return False

    # Disconnect existing
    with _lock:
        old_info = _servers.pop(name, None)
        # Remove registered tools for this server
        tools_to_remove = [t for t, s in _registered_tools.items() if s == name]
        for t in tools_to_remove:
            _registered_tools.pop(t, None)

    if old_info:
        task = old_info.get("_task")
        if task and not task.done():
            _mcp_loop.call_soon_threadsafe(task.cancel)

    # Reconnect
    servers_config = load_mcp_config()
    config = servers_config.get(name)
    if not config:
        return False

    try:
        connect_timeout = config.get("connect_timeout", _DEFAULT_CONNECT_TIMEOUT)
        if "url" in config:
            server_info = _run_on_mcp_loop(_connect_http(name, config), timeout=connect_timeout + 5)
        else:
            server_info = _run_on_mcp_loop(_connect_stdio(name, config), timeout=connect_timeout + 5)
    except Exception as e:
        logger.error("MCP server '%s' reconnect failed: %s", name, e)
        return False

    if not server_info:
        return False

    with _lock:
        _servers[name] = server_info

    register_server_tools(name, server_info)
    logger.info("MCP server '%s' reconnected successfully", name)
    return True
