import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..workspace_manager import manager, WorkspaceStatus

router = APIRouter()

# === 工作区 API ===
@router.get("/api/workspaces")
async def get_workspaces():
    """获取工作区列表"""
    workspaces = manager.list_workspaces()
    return {"workspaces": workspaces}


@router.post("/api/workspaces/{workspace_id}/start")
async def start_workspace(workspace_id: str):
    """启动工作区"""
    try:
        ws = await manager.start_workspace(workspace_id)
        return {"success": True, "workspace": ws.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/workspaces/{workspace_id}/stop")
async def stop_workspace(workspace_id: str):
    """停止工作区"""
    try:
        ws = await manager.stop_workspace(workspace_id)
        return {"success": True, "workspace": ws.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/workspaces/{workspace_id}/hide")
async def hide_workspace(workspace_id: str):
    """隐藏工作区"""
    try:
        manager.hide_workspace(workspace_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/workspaces/{workspace_id}/readme")
async def get_workspace_readme(workspace_id: str):
    """获取工作区的 README.md 内容"""
    ws = manager.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(404, "工作区不存在")
    readme_path = ws.path / "README.md"
    if not readme_path.exists():
        return {"id": workspace_id, "content": f"# {ws.name}\n\n暂无说明文档。"}
    content = readme_path.read_text(encoding="utf-8")
    return {"id": workspace_id, "content": content}


@router.post("/api/workspaces/{workspace_id}/unhide")
async def unhide_workspace(workspace_id: str):
    """取消隐藏工作区"""
    try:
        manager.unhide_workspace(workspace_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/workspaces/refresh")
async def refresh_workspaces():
    """重新扫描工作区目录"""
    manager.discover()
    return {"success": True, "count": len(manager.workspaces)}


@router.post("/api/workspaces/bind")
async def bind_folder_as_workspace(body: dict):
    """绑定本地文件夹为工作区"""
    folder_path = body.get("path", "").strip()
    name = body.get("name", "").strip()
    icon = body.get("icon", "📁")

    if not folder_path:
        raise HTTPException(400, "path 不能为空")

    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(400, f"路径不存在或不是文件夹: {folder_path}")

    # 用文件夹名生成 ID
    if not name:
        name = folder.name

    ws_id = name.lower().replace(" ", "-").replace("_", "-")
    # 去掉非法字符
    ws_id = "".join(c for c in ws_id if c.isalnum() or c == "-")[:30]
    if not ws_id:
        ws_id = "bound-folder"

    # 检查是否已存在
    if ws_id in manager.workspaces:
        raise HTTPException(409, f"工作区 ID 已存在: {ws_id}")

    # 在 workspaces/ 下创建绑定目录（只含 workspace.json）
    from daozhu.config import get_workspace_dir
    ws_dir = get_workspace_dir() / ws_id
    ws_dir.mkdir(exist_ok=True)

    ws_data = {
        "id": ws_id,
        "name": name,
        "icon": icon,
        "color": "#8B5CF6",
        "version": "1.0.0",
        "description": f"绑定文件夹: {folder_path}",
        "port": 0,
        "entry": "",
        "tags": ["本地文件夹"],
        "start_mode": "manual",
        "mode": "bound",
        "bound_path": str(folder),
        "source": "user-bound",
    }

    (ws_dir / "workspace.json").write_text(
        json.dumps(ws_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 重新发现工作区
    manager.discover()
    return {"success": True, "workspace": manager.workspaces[ws_id].to_dict()}


@router.post("/api/workspaces/{workspace_id}/open-folder")
async def open_workspace_folder(workspace_id: str):
    """用系统资源管理器打开工作区文件夹"""
    import subprocess as sp
    import sys as _sys

    ws = manager.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(404, "工作区不存在")

    # 确定要打开的路径
    if ws.mode == "bound" and ws.bound_path:
        target = Path(ws.bound_path)
    else:
        target = ws.path

    if not target.exists():
        raise HTTPException(400, f"路径不存在: {target}")

    # 跨平台打开资源管理器
    if _sys.platform == "win32":
        sp.Popen(["explorer", str(target)])
    elif _sys.platform == "darwin":
        sp.Popen(["open", str(target)])
    else:
        sp.Popen(["xdg-open", str(target)])

    return {"success": True, "path": str(target)}


@router.post("/api/workspaces/reorder")
async def reorder_workspaces(body: dict):
    """更新工作区显示顺序"""
    order = body.get("order", [])  # ["todo", "accobot", "forum"]
    if not order:
        raise HTTPException(400, "order 不能为空")

    for i, ws_id in enumerate(order):
        ws = manager.get_workspace(ws_id)
        if ws:
            # 更新 workspace.json 中的 sort_order
            ws_json_path = ws.path / "workspace.json"
            if ws_json_path.exists():
                data = json.loads(ws_json_path.read_text(encoding="utf-8"))
                data["sort_order"] = i
                ws_json_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    # 重新发现以更新内存中的顺序
    manager.discover()
    return {"success": True}


