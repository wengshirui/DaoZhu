"""Central tool registry for AccoBot.

Simplified from Hermes Agent's registry — same pattern, less complexity.
Each tool file calls `registry.register()` at module level.

Import chain (circular-import safe):
    accobot/tools/registry.py  (no deps on other accobot modules)
           ^
    accobot/tools/*.py  (import registry at module level)
           ^
    accobot/agent.py  (imports registry + triggers tool discovery)
"""

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ToolEntry:
    """Metadata for a single registered tool."""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn",
        "description", "emoji",
    )

    def __init__(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Optional[Callable] = None,
        description: str = "",
        emoji: str = "",
    ):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.description = description or schema.get("description", "")
        self.emoji = emoji


class ToolRegistry:
    """Singleton registry that collects tool schemas + handlers."""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Optional[Callable] = None,
        description: str = "",
        emoji: str = "",
    ) -> None:
        """Register a tool. Called at module-import time by each tool file."""
        self._tools[name] = ToolEntry(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            description=description,
            emoji=emoji,
        )
        logger.debug("Registered tool: %s (toolset=%s)", name, toolset)

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        """Return a registered tool entry by name, or None."""
        return self._tools.get(name)

    def get_all_tool_names(self) -> List[str]:
        """Return sorted list of all registered tool names."""
        return sorted(self._tools.keys())

    def get_definitions(self, tool_names: Optional[Set[str]] = None) -> List[dict]:
        """Return OpenAI-format tool schemas for the requested tools.

        If tool_names is None, returns all available tools.
        Only includes tools whose check_fn() returns True (or have no check_fn).
        """
        result = []
        entries = self._tools.values() if tool_names is None else [
            self._tools[n] for n in sorted(tool_names) if n in self._tools
        ]
        for entry in entries:
            if entry.check_fn:
                try:
                    if not entry.check_fn():
                        continue
                except Exception:
                    continue
            result.append({
                "type": "function",
                "function": {**entry.schema, "name": entry.name},
            })
        return result

    def dispatch(self, name: str, args: dict, **kwargs) -> str:
        """Execute a tool handler by name. Returns JSON string."""
        entry = self.get_entry(name)
        if not entry:
            return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
        try:
            return entry.handler(args, **kwargs)
        except Exception as e:
            logger.exception("Tool %s dispatch error: %s", name, e)
            return json.dumps(
                {"error": f"Tool execution failed: {type(e).__name__}: {e}"},
                ensure_ascii=False,
            )

    def get_toolset_tools(self, toolset: str) -> List[str]:
        """Return tool names belonging to a toolset."""
        return sorted(
            name for name, entry in self._tools.items()
            if entry.toolset == toolset
        )


# Module-level singleton
registry = ToolRegistry()


# ---------------------------------------------------------------------------
# Helper functions for tool response serialization
# ---------------------------------------------------------------------------

def tool_error(message: str, **extra) -> str:
    """Return a JSON error string for tool handlers."""
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def tool_result(data: Any = None, **kwargs) -> str:
    """Return a JSON result string for tool handlers."""
    if data is not None:
        return json.dumps(data, ensure_ascii=False, default=str)
    return json.dumps(kwargs, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------

def discover_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """Import all tool modules in the tools directory to trigger registration."""
    tools_path = tools_dir or Path(__file__).resolve().parent
    imported: List[str] = []

    for path in sorted(tools_path.glob("*.py")):
        if path.name in {"__init__.py", "registry.py"}:
            continue
        mod_name = f"accobot.tools.{path.stem}"
        try:
            importlib.import_module(mod_name)
            imported.append(mod_name)
        except Exception as e:
            logger.warning("Could not import tool module %s: %s", mod_name, e)

    return imported
