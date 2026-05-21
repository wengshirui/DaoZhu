"""Skill tools — list, view, and manage skills.

Toolset: "skills"
Provides the agent with skill discovery and management capabilities.

Inspired by Hermes Agent's tools/skills_tool.py and tools/skill_manager_tool.py.
"""

import json
from accobot.tools.registry import registry, tool_result, tool_error


# =========================================================================
# skill_list — List available skills (compact index)
# =========================================================================

def skill_list(args: dict, **kwargs) -> str:
    """List all available skills with name, description, and category."""
    from accobot.skills.loader import scan_skills

    category = args.get("category", "")
    skills = scan_skills()

    if category:
        skills = [s for s in skills if s.get("category") == category]

    if not skills:
        if category:
            return tool_result(skills=[], message=f"没有找到分类为「{category}」的 Skill")
        return tool_result(skills=[], message="暂无可用的 Skill。你可以通过 skill_manage 创建新的 Skill。")

    lines = [f"📚 可用 Skill（共 {len(skills)} 个）："]
    for s in skills:
        prefix = "📦" if s.get("is_builtin") else "📝"
        cat_label = f" [{s['category']}]" if s.get("category") else ""
        lines.append(f"  {prefix} {s['name']}{cat_label} — {s['description']}")

    return tool_result(
        skills=[{"name": s["name"], "description": s["description"], "category": s.get("category", "")} for s in skills],
        count=len(skills),
        message="\n".join(lines),
    )


# =========================================================================
# skill_view — Load full skill content
# =========================================================================

def skill_view(args: dict, **kwargs) -> str:
    """Load and return the full content of a skill."""
    from accobot.skills.loader import load_skill

    name = args.get("name", "")
    file_path = args.get("file_path")

    if not name:
        return tool_error("请指定 Skill 名称")

    result = load_skill(name, file_path=file_path)

    if not result.get("success"):
        return tool_error(result.get("error", f"Skill '{name}' 加载失败"))

    content = result.get("content", "")
    skill_dir = result.get("skill_dir", "")

    msg_parts = [
        f"📖 Skill: {result.get('name', name)}",
        f"路径: {skill_dir}" if skill_dir else "",
        "",
        content,
    ]

    return tool_result(
        success=True,
        name=result.get("name", name),
        content=content,
        skill_dir=skill_dir,
        is_builtin=result.get("is_builtin", False),
        message="\n".join(msg_parts),
    )


# =========================================================================
# skill_manage — Create, edit, delete skills
# =========================================================================

def skill_manage(args: dict, **kwargs) -> str:
    """Manage skills: create, edit, or delete."""
    from accobot.skills.loader import create_skill, edit_skill, delete_skill

    action = args.get("action", "")
    name = args.get("name", "")

    if not action:
        return tool_error("请指定操作：create / edit / delete")
    if not name:
        return tool_error("请指定 Skill 名称")

    if action == "create":
        content = args.get("content", "")
        if not content:
            return tool_error("创建 Skill 需要提供 content（完整的 SKILL.md 内容，含 frontmatter）")
        category = args.get("category")
        result = create_skill(name, content, category=category)

    elif action == "edit":
        content = args.get("content", "")
        if not content:
            return tool_error("编辑 Skill 需要提供 content（完整的更新后 SKILL.md 内容）")
        result = edit_skill(name, content)

    elif action == "delete":
        result = delete_skill(name)

    else:
        return tool_error(f"未知操作 '{action}'，支持：create / edit / delete")

    if result.get("success"):
        return tool_result(**result)
    else:
        return tool_error(result.get("error", "操作失败"))


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="skill_list",
    toolset="skills",
    schema={
        "name": "skill_list",
        "description": "列出所有可用的 Skill（操作流程知识）。用户问'有哪些技能'、'能做什么'时使用。也用于判断当前任务是否有匹配的 Skill。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "按分类筛选（如 tax、reconciliation、journal）",
                },
            },
        },
    },
    handler=skill_list,
    emoji="📚",
)

registry.register(
    name="skill_view",
    toolset="skills",
    schema={
        "name": "skill_view",
        "description": "加载一个 Skill 的完整内容。当判断某个 Skill 与当前任务相关时，调用此工具获取详细操作步骤。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill 名称",
                },
                "file_path": {
                    "type": "string",
                    "description": "可选：加载 Skill 目录下的子文件（如 references/api.md）",
                },
            },
            "required": ["name"],
        },
    },
    handler=skill_view,
    emoji="📖",
)

registry.register(
    name="skill_manage",
    toolset="skills",
    schema={
        "name": "skill_manage",
        "description": "管理 Skill：创建新 Skill、编辑已有 Skill、删除 Skill。当用户修正了操作流程并同意保存时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "edit", "delete"],
                    "description": "操作类型",
                },
                "name": {
                    "type": "string",
                    "description": "Skill 名称（用作目录名）",
                },
                "content": {
                    "type": "string",
                    "description": "SKILL.md 完整内容（含 YAML frontmatter），create 和 edit 时必填",
                },
                "category": {
                    "type": "string",
                    "description": "分类目录名（仅 create 时可选，如 tax、journal）",
                },
            },
            "required": ["action", "name"],
        },
    },
    handler=skill_manage,
    emoji="🛠️",
)
