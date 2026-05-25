"""
岛主 DaoZhu — 模板引擎
职责: 读取 templates/ 中的模板，替换变量，生成工作区文件
"""

import json
import re
from pathlib import Path
from typing import Optional

from .config import PLATFORM_ROOT, get_workspace_dir

TEMPLATES_DIR = PLATFORM_ROOT / "templates"


def list_templates() -> list[dict]:
    """列出所有可用模板"""
    templates = []
    if not TEMPLATES_DIR.exists():
        return templates

    for item in sorted(TEMPLATES_DIR.iterdir()):
        if not item.is_dir():
            continue
        meta_file = item / "template.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            templates.append(meta)
        except (json.JSONDecodeError, OSError):
            continue

    return templates


def render_template(template_id: str, variables: dict) -> Optional[Path]:
    """
    使用模板生成工作区文件。
    返回生成的工作区目录路径，失败返回 None。
    """
    template_dir = TEMPLATES_DIR / template_id
    meta_file = template_dir / "template.json"

    if not meta_file.exists():
        return None

    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # 目标目录
    workspace_id = variables.get("id", "new-workspace")
    target_dir = get_workspace_dir() / workspace_id

    if target_dir.exists():
        return None  # 已存在，不覆盖

    # 创建目录结构并渲染文件
    for tmpl_file in meta.get("files", []):
        src_path = template_dir / tmpl_file
        if not src_path.exists():
            continue

        # 目标文件路径（去掉 .tmpl 后缀）
        dest_name = tmpl_file.replace(".tmpl", "")
        dest_path = target_dir / dest_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取模板内容并替换变量
        content = src_path.read_text(encoding="utf-8")
        rendered = _render_content(content, variables)
        dest_path.write_text(rendered, encoding="utf-8")

    return target_dir


def _render_content(content: str, variables: dict) -> str:
    """简单模板渲染：替换 {{variable}} 占位符"""
    def replacer(match):
        key = match.group(1).strip()
        value = variables.get(key, match.group(0))
        # JSON 数组特殊处理
        if isinstance(value, list):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return re.sub(r'\{\{(\w+)\}\}', replacer, content)


def get_next_available_port() -> int:
    """获取下一个可用端口"""
    workspace_dir = get_workspace_dir()
    used_ports = set()

    if workspace_dir.exists():
        for item in workspace_dir.iterdir():
            ws_json = item / "workspace.json"
            if ws_json.exists():
                try:
                    data = json.loads(ws_json.read_text(encoding="utf-8"))
                    used_ports.add(data.get("port", 0))
                except (json.JSONDecodeError, OSError):
                    pass

    # 从 7801 开始找可用端口
    for port in range(7801, 7900):
        if port not in used_ports:
            return port

    return 7899
