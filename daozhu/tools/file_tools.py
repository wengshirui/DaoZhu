"""
岛主工具 — 文件操作
让 Agent 能在工作区目录内创建和读取文件，用于自定义代码生成
"""

import json
from pathlib import Path

from .registry import registry
from ..config import get_workspace_dir


def _safe_path(file_path: str) -> Path:
    """确保路径在 workspaces/ 目录内（安全边界）"""
    workspace_dir = get_workspace_dir()
    target = (workspace_dir / file_path).resolve()
    if not str(target).startswith(str(workspace_dir.resolve())):
        raise ValueError("路径越界：只能操作 workspaces/ 目录内的文件")
    return target


async def write_file_tool(file_path: str, content: str) -> str:
    """在工作区目录内写入文件"""
    try:
        target = _safe_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return json.dumps({
            "success": True,
            "message": f"文件已写入: workspaces/{file_path}",
            "size": len(content),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def read_file_tool(file_path: str) -> str:
    """读取工作区目录内的文件"""
    try:
        target = _safe_path(file_path)
        if not target.exists():
            return json.dumps({"error": f"文件不存在: {file_path}"}, ensure_ascii=False)
        content = target.read_text(encoding="utf-8")
        return json.dumps({
            "path": file_path,
            "content": content[:5000],  # 限制返回大小
            "truncated": len(content) > 5000,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def list_files_tool(directory: str = "") -> str:
    """列出工作区目录内的文件"""
    try:
        target = _safe_path(directory) if directory else get_workspace_dir()
        if not target.exists():
            return json.dumps({"error": "目录不存在"}, ensure_ascii=False)

        files = []
        for item in sorted(target.iterdir()):
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            files.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return json.dumps({"directory": directory or "workspaces/", "files": files}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# === 注册工具 ===

registry.register(
    name="write_file",
    description="在工作区目录内创建或覆盖文件。路径相对于 workspaces/ 目录，如 'todo/schema.sql'。用于生成工作区代码。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "相对于 workspaces/ 的文件路径，如 'myapp/app.py'"},
            "content": {"type": "string", "description": "文件内容"},
        },
        "required": ["file_path", "content"],
    },
    handler=write_file_tool,
    category="file",
    emoji="📝",
)

registry.register(
    name="read_file",
    description="读取工作区目录内的文件内容。路径相对于 workspaces/ 目录。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "相对于 workspaces/ 的文件路径"},
        },
        "required": ["file_path"],
    },
    handler=read_file_tool,
    category="file",
    emoji="📖",
)

registry.register(
    name="list_files",
    description="列出工作区目录内的文件和子目录。不传参数则列出所有工作区。",
    parameters={
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "相对于 workspaces/ 的目录路径，如 'todo' 或 'todo/routes'"},
        },
        "required": [],
    },
    handler=list_files_tool,
    category="file",
    emoji="📁",
)
