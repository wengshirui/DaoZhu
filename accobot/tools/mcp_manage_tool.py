"""MCP management tool — let the Agent configure MCP servers via conversation.

Toolset: "config"
Allows the agent to add, remove, enable/disable MCP servers without
requiring the user to edit config.yaml manually.

Example: User says "帮我连接金蝶云" → Agent calls mcp_manage to add the server config.
"""

import json
from accobot.tools.registry import registry, tool_result, tool_error


def mcp_manage(args: dict, **kwargs) -> str:
    """Manage MCP server configuration through the Agent.

    Actions: add, remove, enable, disable, list
    """
    from accobot.config import load_config, save_config

    action = args.get("action", "")
    name = args.get("name", "")

    if not action:
        return tool_error("请指定操作：add / remove / enable / disable / list")

    config = load_config()
    if "mcp_servers" not in config:
        config["mcp_servers"] = {}

    servers = config["mcp_servers"]

    # ── LIST ──
    if action == "list":
        if not servers:
            return tool_result(
                servers=[],
                message="当前没有配置任何 MCP 服务器。可以用 mcp_manage(action='add') 添加。",
            )
        items = []
        for sname, scfg in servers.items():
            enabled = scfg.get("enabled", True)
            transport = "HTTP" if "url" in scfg else "stdio"
            items.append({
                "name": sname,
                "enabled": enabled,
                "transport": transport,
                "command": scfg.get("command", scfg.get("url", "")),
            })
        lines = ["📡 已配置的 MCP 服务器："]
        for item in items:
            status = "🟢" if item["enabled"] else "⚪"
            lines.append(f"  {status} {item['name']} ({item['transport']}) — {item['command']}")
        return tool_result(servers=items, message="\n".join(lines))

    # All other actions need a name
    if not name:
        return tool_error("请指定 MCP 服务器名称")

    # ── ADD ──
    if action == "add":
        command = args.get("command", "")
        url = args.get("url", "")
        server_args = args.get("args", [])
        env = args.get("env", {})
        timeout = args.get("timeout", 120)

        if not command and not url:
            return tool_error("添加 MCP 服务器需要指定 command（本地命令）或 url（远程地址）")

        if name in servers:
            return tool_error(f"MCP 服务器 '{name}' 已存在。如需修改，请先 remove 再 add。")

        new_server = {"enabled": True, "timeout": timeout}
        if url:
            new_server["url"] = url
        else:
            new_server["command"] = command
            if server_args:
                new_server["args"] = server_args
        if env:
            new_server["env"] = env

        servers[name] = new_server
        save_config(config)

        return tool_result(
            success=True,
            name=name,
            message=f"✅ MCP 服务器 '{name}' 已添加。重启 AccoBot 或刷新页面后生效。",
        )

    # ── REMOVE ──
    elif action == "remove":
        if name not in servers:
            return tool_error(f"MCP 服务器 '{name}' 不存在")
        if name == "playwright":
            return tool_error("Playwright 是系统内置 MCP 服务器，不允许删除。可以用 disable 禁用。")
        del servers[name]
        save_config(config)
        return tool_result(success=True, message=f"✅ MCP 服务器 '{name}' 已删除")

    # ── ENABLE ──
    elif action == "enable":
        if name not in servers:
            return tool_error(f"MCP 服务器 '{name}' 不存在")
        servers[name]["enabled"] = True
        save_config(config)
        return tool_result(success=True, message=f"✅ MCP 服务器 '{name}' 已启用")

    # ── DISABLE ──
    elif action == "disable":
        if name not in servers:
            return tool_error(f"MCP 服务器 '{name}' 不存在")
        servers[name]["enabled"] = False
        save_config(config)
        return tool_result(success=True, message=f"✅ MCP 服务器 '{name}' 已禁用")

    else:
        return tool_error(f"未知操作 '{action}'，支持：add / remove / enable / disable / list")


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="mcp_manage",
    toolset="config",
    schema={
        "name": "mcp_manage",
        "description": "管理 MCP 服务器配置（添加/删除/启用/禁用/列表）。用户说'连接金蝶云'、'添加XX服务'、'关闭浏览器自动化'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove", "enable", "disable", "list"],
                    "description": "操作类型",
                },
                "name": {
                    "type": "string",
                    "description": "MCP 服务器名称（如 playwright、kingdee）",
                },
                "command": {
                    "type": "string",
                    "description": "本地命令（如 npx、python），add 时与 url 二选一",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "命令参数列表",
                },
                "url": {
                    "type": "string",
                    "description": "远程 MCP 服务器 URL，add 时与 command 二选一",
                },
                "env": {
                    "type": "object",
                    "description": "环境变量（如 {\"API_KEY\": \"xxx\"}）",
                },
                "timeout": {
                    "type": "integer",
                    "description": "工具调用超时秒数（默认 120）",
                },
            },
            "required": ["action"],
        },
    },
    handler=mcp_manage,
    emoji="🔌",
)
