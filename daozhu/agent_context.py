"""
岛主 DaoZhu — Agent Context 构建（#079 Phase 4）
负责构建每轮对话的动态上下文（工作区列表、API hint、统计等）。
从 agent.py 提取，独立可测试。
"""

import json
import re
from pathlib import Path
from typing import Optional


def build_stats_context() -> str:
    """构建使用统计上下文，触发 AI 主动建议优化"""
    from .tool_log_db import get_tool_stats, get_stale_tools

    parts = []
    stats = get_tool_stats(days=7)
    if stats:
        failing = [s for s in stats if s.get("success_rate", 100) < 70]
        if failing:
            names = ", ".join(s["tool_name"] for s in failing[:3])
            parts.append(f"⚠️ 以下工具最近失败率较高: {names}。如果合适，可以建议用户优化或禁用。")

    stale = get_stale_tools(days=30)
    if stale:
        names = ", ".join(s["tool_name"] for s in stale[:3])
        parts.append(f"💤 以下工具超过30天未使用: {names}。可以建议用户是否需要禁用。")

    if parts:
        return "[以下是资源使用情况，在合适时机自然地提出优化建议：]\n" + "\n".join(parts)
    return ""


def get_workspace_api_hint(ws_id: str, ws_path) -> str:
    """
    从工作区的路由文件中提取 API 端点摘要。
    让 AI 知道确切的 API 路径，避免猜测导致的幻觉。
    """
    routes_dir = Path(ws_path) / "routes"
    if not routes_dir.exists():
        routes_file = Path(ws_path) / "routes.py"
        if routes_file.exists():
            return _extract_routes_from_file(routes_file, "/")
        return ""

    # 解析 __init__.py 获取 prefix 映射
    init_file = routes_dir / "__init__.py"
    prefix_map = {}
    if init_file.exists():
        try:
            content = init_file.read_text(encoding="utf-8")
            for m in re.finditer(r'include_router\(\s*(\w+)_router.*?prefix\s*=\s*["\']([^"\']+)', content):
                prefix_map[m.group(1)] = m.group(2)
        except Exception:
            pass

    hints = []
    for py_file in sorted(routes_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        stem = py_file.stem
        prefix = prefix_map.get(stem, f"/{stem}")
        extracted = _extract_routes_from_file(py_file, prefix)
        if extracted:
            hints.append(extracted)

    return "\n".join(hints) if hints else ""


def _extract_routes_from_file(filepath, prefix: str = "") -> str:
    """从 Python 路由文件中提取 API 端点"""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return ""

    pattern = r'@router\.(get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']'
    matches = re.findall(pattern, content)
    if not matches:
        return ""

    lines = []
    for method, path in matches[:10]:
        full_path = prefix.rstrip("/") + path if path != "/" else prefix
        func_pattern = rf'@router\.{method}\s*\(\s*["\']({re.escape(path)})["\'].*?\n\s*(?:async\s+)?def\s+\w+.*?\n\s*"""([^"]*?)"""'
        doc_match = re.search(func_pattern, content, re.DOTALL)
        desc = doc_match.group(2).strip().split('\n')[0] if doc_match else ""
        desc_str = f" — {desc}" if desc else ""
        lines.append(f"    {method.upper()} {full_path}{desc_str}")

    return "\n".join(lines)


def build_dynamic_context(memory_context: str = "") -> list[str]:
    """构建动态上下文部分（工作区列表 + 统计 + 记忆）"""
    from .skill_loader import get_skills_summary
    from .workspace_manager import manager

    context_parts = []

    skills_summary = get_skills_summary()
    if skills_summary:
        context_parts.append(skills_summary)

    # 工作区列表 + API 路由提示
    ws_lines = []
    for ws in manager.workspaces.values():
        if ws.hidden:
            continue
        api_hint = get_workspace_api_hint(ws.id, ws.path)
        if api_hint:
            ws_lines.append(f"  [{ws.id}] {ws.name}（端口 {ws.port}）\n{api_hint}")
        else:
            ws_lines.append(f"  [{ws.id}] {ws.name}（端口 {ws.port}）")
    if ws_lines:
        context_parts.append("[可用工作区 — 用 call_workspace_api 操作，必须使用下面列出的精确路径：]\n" + "\n".join(ws_lines))

    # 统计
    stats_context = build_stats_context()
    if stats_context:
        context_parts.append(stats_context)

    # 记忆
    if memory_context:
        context_parts.append(memory_context)

    return context_parts


# ─── 生命档案上下文（#084）────────────────────────────────────

def build_lifecycle_block() -> str:
    """
    构建 SYSTEM_PROMPT 中的"生命档案"区块内容。
    从 lifecycle.db 读取当前 agent 状态 + 前代遗产。
    """
    try:
        from .lifecycle_db import (
            get_current_agent, get_alive_seconds,
            get_previous_agent, get_inherited_config,
            get_sleep_stats,
        )
    except Exception:
        return "（生命档案暂不可用）"

    agent = get_current_agent()
    if not agent:
        return "- 身份：第 1 代岛管理员（新生）\n- 状态：刚刚诞生，尚无历史数据"

    gen = agent["generation"]
    alive = get_alive_seconds()

    # 格式化存活时间
    if alive < 3600:
        alive_str = f"{alive/60:.0f} 分钟"
    elif alive < 86400:
        alive_str = f"{alive/3600:.1f} 小时"
    else:
        alive_str = f"{alive/86400:.1f} 天"

    from datetime import datetime
    born_str = datetime.fromtimestamp(agent["born_at"]).strftime("%Y-%m-%d %H:%M")

    lines = [
        f"- 身份：第 {gen} 代岛管理员",
        f"- 存活：{alive_str}（出生于 {born_str}）",
    ]

    # 前代遗产
    prev = get_previous_agent(gen)
    if prev:
        if prev.get("death_reason_user"):
            lines.append(f"\n### 前代教训")
            lines.append(f"- 第 {gen-1} 代死因（用户）：\"{prev['death_reason_user']}\"")
        if prev.get("death_reason_agent"):
            lines.append(f"- 第 {gen-1} 代遗言：\"{prev['death_reason_agent']}\"")

        # 继承配置
        inherited = get_inherited_config(prev["id"])
        if inherited.get("preferences"):
            lines.append(f"- 继承偏好：{inherited['preferences']}")

    # 休眠统计
    sleep_stats = get_sleep_stats(agent["id"])
    if sleep_stats["count"] > 0:
        lines.append(f"\n### 用户作息")
        lines.append(f"- 休眠 {sleep_stats['count']} 次，最长 {sleep_stats['max_hours']} 小时")

    # 使命
    lines.append(f"\n### 你的使命")
    lines.append("你的目标是更了解用户、更好地帮助用户。你的寿命取决于用户是否觉得你有用。")
    if prev and prev.get("death_reason_user"):
        lines.append(f"前代因为「{prev['death_reason_user']}」被终结——记住这个教训。")

    return "\n".join(lines)
