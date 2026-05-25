"""
岛主工具 — 模板管理
让 Agent 能使用模板快速生成工作区
"""

import json
from .registry import registry


async def list_templates_tool() -> str:
    """列出所有可用的工作区模板"""
    from ..template_engine import list_templates
    templates = list_templates()
    return json.dumps({"templates": templates}, ensure_ascii=False)


async def create_from_template_tool(
    template_id: str,
    workspace_id: str,
    name: str,
    icon: str = "📦",
    color: str = "#6366F1",
    description: str = "",
    table_name: str = "items",
    entity_name: str = "条目",
    tags: str = "[]",
) -> str:
    """使用模板创建新工作区"""
    from ..template_engine import render_template, get_next_available_port
    from datetime import date

    port = get_next_available_port()

    # 解析 tags
    try:
        tags_list = json.loads(tags) if isinstance(tags, str) else tags
    except json.JSONDecodeError:
        tags_list = []

    variables = {
        "id": workspace_id,
        "name": name,
        "icon": icon,
        "color": color,
        "port": port,
        "description": description,
        "table_name": table_name,
        "entity_name": entity_name,
        "tags": tags_list,
        "date": date.today().isoformat(),
    }

    result_path = render_template(template_id, variables)
    if result_path is None:
        return json.dumps({"error": f"模板渲染失败（模板不存在或工作区已存在）"}, ensure_ascii=False)

    # 刷新工作区列表
    from ..workspace_manager import manager
    manager.discover()

    return json.dumps({
        "success": True,
        "message": f"工作区 '{name}' 已创建，端口 {port}",
        "workspace_id": workspace_id,
        "port": port,
        "path": str(result_path),
    }, ensure_ascii=False)


# === 注册工具 ===

registry.register(
    name="list_templates",
    description="列出所有可用的工作区模板，包括模板名称、描述和所需变量。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=list_templates_tool,
    category="template",
    emoji="📋",
)

registry.register(
    name="create_from_template",
    description="使用模板快速创建新工作区。需要指定模板ID、工作区ID、名称等信息。",
    parameters={
        "type": "object",
        "properties": {
            "template_id": {"type": "string", "description": "模板 ID，如 'crud-basic'"},
            "workspace_id": {"type": "string", "description": "工作区 ID（kebab-case），如 'reading-notes'"},
            "name": {"type": "string", "description": "工作区显示名称，如 '读书笔记'"},
            "icon": {"type": "string", "description": "emoji 图标，如 '📚'"},
            "color": {"type": "string", "description": "主题色 HEX，如 '#10B981'"},
            "description": {"type": "string", "description": "一句话描述"},
            "table_name": {"type": "string", "description": "数据库主表名，如 'notes'"},
            "entity_name": {"type": "string", "description": "实体中文名，如 '笔记'"},
            "tags": {"type": "string", "description": "标签 JSON 数组，如 '[\"阅读\",\"笔记\"]'"},
        },
        "required": ["template_id", "workspace_id", "name"],
    },
    handler=create_from_template_tool,
    category="template",
    emoji="🏗️",
)
