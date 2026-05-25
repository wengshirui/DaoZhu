"""
岛主 DaoZhu — Skill 加载器
职责: 扫描 skills/ 目录，读取 SKILL.md，供 Agent 使用
参考: Hermes-Agent agent/skill_commands.py（扫描 skills/ 注入为 user message）
"""

from pathlib import Path
from typing import Optional

from .config import PLATFORM_ROOT

SKILLS_DIR = PLATFORM_ROOT / "skills"


def discover_skills() -> list[dict]:
    """
    扫描 skills/ 目录，发现所有可用 skill。
    每个 skill 是一个包含 SKILL.md 的子目录。
    """
    skills = []
    if not SKILLS_DIR.exists():
        return skills

    for item in sorted(SKILLS_DIR.iterdir()):
        if not item.is_dir():
            continue
        skill_file = item / "SKILL.md"
        if not skill_file.exists():
            continue

        skill_id = item.name
        content = skill_file.read_text(encoding="utf-8")
        meta = _parse_skill_meta(content, skill_id)
        skills.append(meta)

    return skills


def load_skill(skill_id: str) -> Optional[str]:
    """加载单个 skill 的完整内容"""
    skill_file = SKILLS_DIR / skill_id / "SKILL.md"
    if not skill_file.exists():
        return None
    return skill_file.read_text(encoding="utf-8")


def get_active_skills() -> list[str]:
    """获取当前激活的 skill 内容列表（用于注入 Agent）"""
    skills = discover_skills()
    contents = []
    for skill in skills:
        content = load_skill(skill["id"])
        if content:
            # 截取前 2000 字符避免 token 过多
            truncated = content[:2000]
            if len(content) > 2000:
                truncated += "\n\n[... 内容已截断 ...]"
            contents.append(truncated)
    return contents


def get_skills_summary() -> str:
    """获取所有 skill 的摘要（注入 system prompt）"""
    skills = discover_skills()
    if not skills:
        return ""

    lines = ["## 你拥有的技能\n"]
    for s in skills:
        lines.append(f"- **{s['name']}**: {s['description']}")
    return "\n".join(lines)


def _parse_skill_meta(content: str, skill_id: str) -> dict:
    """从 SKILL.md 内容中解析元信息"""
    lines = content.split("\n")

    # 提取标题
    name = skill_id
    for line in lines:
        if line.startswith("# "):
            name = line[2:].strip()
            break

    # 提取描述（第一个 ## 描述 下面的内容，或第一段非空文本）
    description = ""
    in_desc = False
    for line in lines:
        if "## 描述" in line or "## Description" in line.lower():
            in_desc = True
            continue
        if in_desc:
            if line.startswith("##") or line.startswith("---"):
                break
            if line.strip():
                description += line.strip() + " "
    
    if not description:
        # fallback: 取 > 引用行
        for line in lines:
            if line.startswith("> ") and "来源" not in line:
                description = line[2:].strip()
                break

    return {
        "id": skill_id,
        "name": name,
        "description": description.strip()[:100],
        "path": str(SKILLS_DIR / skill_id / "SKILL.md"),
    }
