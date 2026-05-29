"""
岛主工具 — 工作区 API 调用
让 Agent 能直接操作工作区的数据（添加待办、记账、查宠物等）
工具描述动态生成：自动发现所有工作区，Agent 无需硬编码。
"""

import json
import httpx

from .registry import registry


def _build_workspace_hints() -> str:
    """扫描所有工作区，生成 API 调用提示"""
    from ..workspace_manager import manager
    hints = []
    for ws in manager.workspaces.values():
        if ws.hidden:
            continue
        hints.append(f"- {ws.id}: {ws.name}（{ws.description or ''}）端口 {ws.port}")
    return "\n".join(hints) if hints else "（暂无工作区）"


async def call_workspace_api_tool(
    workspace_id: str,
    method: str = "GET",
    path: str = "/",
    body: str = "",
) -> str:
    """调用工作区的 API 接口"""
    from ..workspace_manager import manager

    ws = manager.get_workspace(workspace_id)
    if not ws:
        return json.dumps({"error": f"工作区不存在: {workspace_id}"}, ensure_ascii=False)

    # 如果工作区未运行，先启动
    if ws.status.value != "running":
        try:
            ws = await manager.start_workspace(workspace_id)
        except Exception as e:
            return json.dumps({"error": f"启动工作区失败: {e}"}, ensure_ascii=False)

    url = f"http://127.0.0.1:{ws.port}/api{path}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if method.upper() == "GET":
                resp = await client.get(url)
            elif method.upper() == "POST":
                resp = await client.post(
                    url,
                    content=body if body else None,
                    headers={"Content-Type": "application/json"} if body else {},
                )
            elif method.upper() == "PUT":
                resp = await client.put(
                    url,
                    content=body if body else None,
                    headers={"Content-Type": "application/json"} if body else {},
                )
            elif method.upper() == "DELETE":
                resp = await client.delete(url)
            else:
                return json.dumps({"error": f"不支持的方法: {method}"}, ensure_ascii=False)

            if resp.status_code >= 400:
                return json.dumps({
                    "error": f"API 返回 {resp.status_code}",
                    "detail": resp.text[:500],
                }, ensure_ascii=False)

            return resp.text

    except httpx.ConnectError:
        return json.dumps({"error": "无法连接到工作区服务"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# === 注册工具 ===

registry.register(
    name="call_workspace_api",
    description="""调用工作区的 API 接口来操作数据。
常用路径模式: GET /资源/ (列表), GET /资源/{id} (详情), POST /资源/ (创建), DELETE /资源/{id} (删除)
如果工作区未运行会自动启动。调用前先用 list_workspaces 确认工作区 ID。""",
    parameters={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string", "description": "工作区 ID，如 'todo' 或 'accobot'"},
            "method": {"type": "string", "description": "HTTP 方法: GET/POST/PUT/DELETE", "enum": ["GET", "POST", "PUT", "DELETE"]},
            "path": {"type": "string", "description": "API 路径，如 '/tasks/' 或 '/vouchers/'"},
            "body": {"type": "string", "description": "请求体 JSON 字符串（POST/PUT 时使用）"},
        },
        "required": ["workspace_id", "method", "path"],
    },
    handler=call_workspace_api_tool,
    category="workspace",
    emoji="🔌",
)
