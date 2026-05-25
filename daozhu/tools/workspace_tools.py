"""
岛主工具 — 工作区管理
让 Agent 能启停、查询工作区
"""

import json
from .registry import registry


async def list_workspaces_tool() -> str:
    """列出所有工作区及其状态"""
    from ..workspace_manager import manager
    workspaces = manager.list_workspaces(include_hidden=False)
    return json.dumps({"workspaces": workspaces}, ensure_ascii=False)


async def start_workspace_tool(workspace_id: str) -> str:
    """启动指定工作区"""
    from ..workspace_manager import manager
    try:
        ws = await manager.start_workspace(workspace_id)
        return json.dumps({
            "success": True,
            "message": f"工作区 {ws.name} 已启动，端口 {ws.port}",
            "port": ws.port,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def stop_workspace_tool(workspace_id: str) -> str:
    """停止指定工作区"""
    from ..workspace_manager import manager
    try:
        ws = await manager.stop_workspace(workspace_id)
        return json.dumps({
            "success": True,
            "message": f"工作区 {ws.name} 已停止",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def get_workspace_info_tool(workspace_id: str) -> str:
    """获取工作区详细信息"""
    from ..workspace_manager import manager
    ws = manager.get_workspace(workspace_id)
    if not ws:
        return json.dumps({"error": f"工作区不存在: {workspace_id}"}, ensure_ascii=False)
    return json.dumps(ws.to_dict(), ensure_ascii=False)


# === 注册工具 ===

registry.register(
    name="list_workspaces",
    description="列出岛上所有工作区及其运行状态（running/stopped/crashed）",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=list_workspaces_tool,
    category="workspace",
    emoji="🏠",
)

registry.register(
    name="start_workspace",
    description="启动指定的工作区。需要提供工作区 ID。",
    parameters={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string", "description": "工作区 ID，如 'todo'、'finance'"}
        },
        "required": ["workspace_id"],
    },
    handler=start_workspace_tool,
    category="workspace",
    emoji="▶️",
)

registry.register(
    name="stop_workspace",
    description="停止指定的工作区。",
    parameters={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string", "description": "工作区 ID"}
        },
        "required": ["workspace_id"],
    },
    handler=stop_workspace_tool,
    category="workspace",
    emoji="⏹️",
)

registry.register(
    name="get_workspace_info",
    description="获取工作区的详细信息，包括名称、描述、端口、状态等。",
    parameters={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string", "description": "工作区 ID"}
        },
        "required": ["workspace_id"],
    },
    handler=get_workspace_info_tool,
    category="workspace",
    emoji="ℹ️",
)
