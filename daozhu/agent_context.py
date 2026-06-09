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
