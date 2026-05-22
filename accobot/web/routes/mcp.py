"""MCP servers, Skills, and Browser check routes."""

import os
from fastapi import APIRouter

from accobot.config import load_config, save_config

router = APIRouter()


@router.get("/api/browser/check")
async def browser_check():
    """Check if a Chromium-family browser is available for Playwright MCP."""
    import shutil
    import sys

    candidates = []
    if sys.platform == "win32":
        candidates = [
            "chrome", "chromium", "msedge", "brave",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "chromium", "google-chrome",
        ]
    else:
        candidates = ["chromium", "chromium-browser", "google-chrome", "brave-browser", "microsoft-edge"]

    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return {"available": True, "browser": found}
        if os.path.isfile(candidate):
            return {"available": True, "browser": candidate}

    npx = shutil.which("npx")
    if npx:
        return {"available": True, "browser": "playwright-bundled (via npx)", "note": "Playwright MCP will download its own browser on first use"}

    return {"available": False, "error": "未找到 Chromium 系浏览器。请安装 Chrome、Edge 或 Brave。"}


@router.get("/api/skills/list")
async def skills_list_api():
    """Return list of available skills for the UI capabilities panel."""
    try:
        from accobot.skills.loader import scan_skills
        skills = scan_skills()
        return {"skills": [{"name": s["name"], "description": s["description"], "category": s.get("category", "")} for s in skills]}
    except Exception as e:
        return {"skills": [], "error": str(e)}


@router.get("/api/mcp/status")
async def mcp_status():
    """Return status of configured MCP servers."""
    try:
        from accobot.mcp.client import get_mcp_status
        servers = get_mcp_status()
        return {"servers": servers}
    except ImportError:
        return {"servers": [], "note": "MCP SDK not installed (pip install 'accobot[mcp]')"}
    except Exception as e:
        return {"servers": [], "error": str(e)}


@router.post("/api/mcp/reconnect")
async def mcp_reconnect(request: dict):
    """Reconnect a specific MCP server."""
    try:
        from accobot.mcp.client import reconnect_server
        name = request.get("name", "")
        if not name:
            return {"success": False, "error": "请指定服务器名称"}
        ok = reconnect_server(name)
        if ok:
            return {"success": True, "message": f"MCP server '{name}' 已重连"}
        return {"success": False, "error": f"MCP server '{name}' 重连失败"}
    except ImportError:
        return {"success": False, "error": "MCP SDK 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/mcp/add")
async def mcp_add_server(request: dict):
    """Add a new MCP server via Web UI."""
    name = request.get("name", "").strip()
    if not name:
        return {"success": False, "error": "服务器名称不能为空"}

    config = load_config()
    if "mcp_servers" not in config:
        config["mcp_servers"] = {}

    if name in config["mcp_servers"]:
        return {"success": False, "error": f"服务器 '{name}' 已存在"}

    server_type = request.get("type", "stdio")
    new_server = {"enabled": True, "timeout": 120}

    if server_type == "http":
        url = request.get("url", "").strip()
        if not url:
            return {"success": False, "error": "请输入服务器 URL"}
        new_server["url"] = url
    else:
        command = request.get("command", "").strip()
        if not command:
            return {"success": False, "error": "请输入命令"}
        new_server["command"] = command
        args_str = request.get("args", "").strip()
        if args_str:
            new_server["args"] = [a.strip() for a in args_str.split(",") if a.strip()]

    config["mcp_servers"][name] = new_server
    save_config(config)

    return {"success": True, "message": f"MCP 服务器 '{name}' 已添加，刷新页面后生效"}


@router.post("/api/mcp/remove")
async def mcp_remove_server(request: dict):
    """Remove an MCP server via Web UI."""
    name = request.get("name", "").strip()
    if not name:
        return {"success": False, "error": "请指定服务器名称"}
    if name == "playwright":
        return {"success": False, "error": "Playwright 是内置服务器，不能删除（可以禁用）"}

    config = load_config()
    servers = config.get("mcp_servers", {})
    if name not in servers:
        return {"success": False, "error": f"服务器 '{name}' 不存在"}

    del servers[name]
    save_config(config)
    return {"success": True, "message": f"MCP 服务器 '{name}' 已删除"}


@router.post("/api/mcp/toggle")
async def mcp_toggle_server(request: dict):
    """Enable/disable an MCP server via Web UI."""
    name = request.get("name", "").strip()
    enabled = request.get("enabled", True)

    config = load_config()
    servers = config.get("mcp_servers", {})
    if name not in servers:
        return {"success": False, "error": f"服务器 '{name}' 不存在"}

    servers[name]["enabled"] = enabled
    save_config(config)
    status = "启用" if enabled else "禁用"
    return {"success": True, "message": f"MCP 服务器 '{name}' 已{status}"}
