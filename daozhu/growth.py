"""
岛主 DaoZhu — Agent 成长引擎（核心逻辑）
职责: 分析用户对话模式 + 自我优化 + 主动服务
触发: 定时任务自动执行 / 平台启动时检查
"""

import json
import logging
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from .config import PLATFORM_ROOT

logger = logging.getLogger(__name__)

GROWTH_DB_PATH = PLATFORM_ROOT / "growth.db"

# 核心工具（永不建议禁用）
CORE_TOOLS = {
    "list_workspaces", "call_workspace_api", "start_workspace",
    "stop_workspace", "get_workspace_info", "list_templates",
    "create_from_template", "write_file", "read_file", "list_files",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS growth_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    suggestions TEXT DEFAULT '[]',
    auto_executed TEXT DEFAULT '[]',
    insights TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def _get_growth_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(GROWTH_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def _get_chat_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(PLATFORM_ROOT / "chat.db"))
    conn.row_factory = sqlite3.Row
    return conn


def _get_memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(PLATFORM_ROOT / "memory.db"))
    conn.row_factory = sqlite3.Row
    return conn


# === 三维度分析 ===

def _analyze_user_patterns(chat_conn: sqlite3.Connection) -> dict:
    """维度 1：分析用户对话模式"""
    msgs = chat_conn.execute(
        "SELECT content, created_at FROM messages WHERE role='user' AND active=1 "
        "ORDER BY created_at DESC LIMIT 100"
    ).fetchall()

    if not msgs:
        return {"total_msgs": 0, "patterns": [], "peak_hour": None, "repeated": []}

    patterns = Counter()
    for msg in msgs:
        text = msg["content"] or ""
        if "工作区" in text or "建" in text or "创建" in text:
            patterns["工作区管理"] += 1
        elif "天气" in text or "查" in text or "搜" in text:
            patterns["信息查询"] += 1
        elif "待办" in text or "任务" in text or "记" in text:
            patterns["任务管理"] += 1
        elif "启动" in text or "打开" in text or "停止" in text:
            patterns["工作区操控"] += 1
        else:
            patterns["通用对话"] += 1

    hours = Counter()
    for msg in msgs:
        if msg["created_at"]:
            try:
                h = datetime.fromisoformat(msg["created_at"]).hour
                hours[h] += 1
            except (ValueError, TypeError):
                pass

    peak_hour = hours.most_common(1)[0][0] if hours else None

    seen = Counter()
    for msg in msgs:
        key = (msg["content"] or "")[:25].strip()
        if len(key) > 5:
            seen[key] += 1
    repeated = [(k, v) for k, v in seen.items() if v >= 2]
    repeated.sort(key=lambda x: -x[1])

    return {
        "total_msgs": len(msgs),
        "patterns": patterns.most_common(5),
        "peak_hour": peak_hour,
        "repeated": repeated[:5],
    }


def _analyze_self_improvement(chat_conn: sqlite3.Connection) -> dict:
    """维度 2：自我优化空间"""
    undo_count = chat_conn.execute(
        "SELECT COUNT(*) FROM messages WHERE active=0 AND role='assistant'"
    ).fetchone()[0]
    total_assistant = chat_conn.execute(
        "SELECT COUNT(*) FROM messages WHERE role='assistant'"
    ).fetchone()[0]

    tool_stats = chat_conn.execute("""
        SELECT tool_name, COUNT(*) as calls, SUM(success) as ok,
               ROUND(AVG(duration_ms)) as avg_ms
        FROM tool_logs WHERE created_at > datetime('now', '-7 days')
        GROUP BY tool_name ORDER BY calls DESC
    """).fetchall()

    failing_tools = []
    for t in tool_stats:
        rate = (t["ok"] / t["calls"] * 100) if t["calls"] > 0 else 100
        if rate < 70:
            errors = chat_conn.execute(
                "SELECT error FROM tool_logs WHERE tool_name=? AND success=0 "
                "ORDER BY created_at DESC LIMIT 3",
                (t["tool_name"],)
            ).fetchall()
            failing_tools.append({
                "name": t["tool_name"],
                "rate": rate,
                "calls": t["calls"],
                "errors": [e["error"][:60] for e in errors if e["error"]],
                "is_core": t["tool_name"] in CORE_TOOLS,
            })

    return {
        "undo_count": undo_count,
        "total_replies": total_assistant,
        "undo_rate": (undo_count / total_assistant * 100) if total_assistant > 0 else 0,
        "failing_tools": failing_tools,
    }


def _analyze_proactive(memory_conn: sqlite3.Connection) -> dict:
    """维度 3：主动服务机会"""
    profiles = memory_conn.execute("SELECT id, key, value FROM user_profile").fetchall()
    profile_keys = Counter(p["key"] for p in profiles)
    duplicates = [(k, v) for k, v in profile_keys.items() if v > 1]
    knowledge_count = memory_conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]

    return {
        "profile_count": len(profiles),
        "duplicate_profiles": duplicates,
        "knowledge_count": knowledge_count,
    }


# === 自动成长动作 ===

def _auto_grow(insights: dict, memory_conn: sqlite3.Connection) -> list[str]:
    """执行🟢级自动成长动作"""
    actions = []

    # 1. 合并重复画像
    duplicates = insights.get("proactive", {}).get("duplicate_profiles", [])
    for key, count in duplicates:
        rows = memory_conn.execute(
            "SELECT id FROM user_profile WHERE key=? ORDER BY updated_at DESC", (key,)
        ).fetchall()
        if len(rows) > 1:
            old_ids = [r["id"] for r in rows[1:]]
            memory_conn.execute(
                f"DELETE FROM user_profile WHERE id IN ({','.join('?' * len(old_ids))})", old_ids
            )
            actions.append(f"🟢 合并重复画像「{key}」({count}→1)")

    # 2. 从高频模式补充画像
    patterns = insights.get("user_patterns", {}).get("patterns", [])
    if patterns:
        top = patterns[0][0]
        existing = memory_conn.execute(
            "SELECT value FROM user_profile WHERE key='主要用途'"
        ).fetchone()
        if not existing:
            memory_conn.execute(
                "INSERT INTO user_profile (key, value, source, confidence, updated_at) "
                "VALUES ('主要用途', ?, 'auto_growth', 0.7, datetime('now','localtime'))",
                (f"{top}（基于近期对话分析）",)
            )
            actions.append(f"🟢 记录画像: 主要用途 = {top}")

    # 3. 记录活跃时段
    peak = insights.get("user_patterns", {}).get("peak_hour")
    if peak is not None:
        existing = memory_conn.execute(
            "SELECT value FROM user_profile WHERE key='活跃时段'"
        ).fetchone()
        if not existing:
            memory_conn.execute(
                "INSERT INTO user_profile (key, value, source, confidence, updated_at) "
                "VALUES ('活跃时段', ?, 'auto_growth', 0.6, datetime('now','localtime'))",
                (f"主要在 {peak}:00 前后使用",)
            )
            actions.append(f"🟢 记录画像: 活跃时段 = {peak}:00")

    # 4. 清理过期知识
    cutoff = (datetime.now() - timedelta(days=60)).isoformat()
    old = memory_conn.execute(
        "SELECT id FROM knowledge WHERE category='tool_failure' AND created_at < ?", (cutoff,)
    ).fetchall()
    if old:
        ids = [r["id"] for r in old]
        memory_conn.execute(
            f"DELETE FROM knowledge WHERE id IN ({','.join('?' * len(ids))})", ids
        )
        actions.append(f"🟢 清理 {len(ids)} 条过期失败记录")

    memory_conn.commit()
    return actions


def _generate_suggestions(insights: dict) -> list[dict]:
    """生成建议"""
    suggestions = []

    # 从重复模式推断自动化机会
    repeated = insights.get("user_patterns", {}).get("repeated", [])
    for pattern, count in repeated[:3]:
        if count >= 3:
            suggestions.append({
                "level": "yellow",
                "text": f"重复请求「{pattern[:15]}...」{count}次，建议自动化",
                "action": "suggest_automation",
                "target": pattern,
                "executed": False,
            })

    # 工具问题
    for tool in insights.get("self_improvement", {}).get("failing_tools", []):
        error_sample = tool["errors"][0] if tool["errors"] else "未知"
        if tool["is_core"]:
            suggestions.append({
                "level": "red",
                "text": f"核心工具 {tool['name']} 失败率 {100-tool['rate']:.0f}%: {error_sample}",
                "action": "investigate", "target": tool["name"], "executed": False,
            })
        else:
            suggestions.append({
                "level": "yellow",
                "text": f"工具 {tool['name']} 失败率 {100-tool['rate']:.0f}%，建议禁用",
                "action": "disable_tool", "target": tool["name"], "executed": False,
            })

    return suggestions


# === 对外接口 ===

def run_growth() -> dict:
    """执行一次完整的成长分析（同步，供定时任务或 API 调用）"""
    today = datetime.now().strftime("%Y-%m-%d")

    chat_conn = _get_chat_db()
    memory_conn = _get_memory_db()

    # 三维度分析
    user_patterns = _analyze_user_patterns(chat_conn)
    self_improvement = _analyze_self_improvement(chat_conn)
    proactive = _analyze_proactive(memory_conn)

    insights = {
        "user_patterns": user_patterns,
        "self_improvement": self_improvement,
        "proactive": proactive,
    }

    # 自动执行
    auto_actions = _auto_grow(insights, memory_conn)

    # 生成建议
    suggestions = _generate_suggestions(insights)

    # 摘要
    parts = [f"分析 {user_patterns['total_msgs']} 条对话"]
    if user_patterns["patterns"]:
        parts.append(f"高频: {user_patterns['patterns'][0][0]}")
    if user_patterns["repeated"]:
        parts.append(f"{len(user_patterns['repeated'])} 个重复模式")
    if self_improvement["failing_tools"]:
        parts.append(f"{len(self_improvement['failing_tools'])} 工具需关注")
    summary = " · ".join(parts)

    # 存储
    stored_insights = {
        "patterns": user_patterns["patterns"],
        "peak_hour": user_patterns["peak_hour"],
        "repeated_count": len(user_patterns["repeated"]),
        "undo_rate": self_improvement["undo_rate"],
        "profile_count": proactive["profile_count"],
    }

    growth_db = _get_growth_db()
    growth_db.execute(
        "INSERT INTO growth_reports (date, summary, suggestions, auto_executed, insights) "
        "VALUES (?,?,?,?,?)",
        (today, summary,
         json.dumps(suggestions, ensure_ascii=False),
         json.dumps(auto_actions, ensure_ascii=False),
         json.dumps(stored_insights, ensure_ascii=False)),
    )
    growth_db.commit()
    growth_db.close()
    chat_conn.close()
    memory_conn.close()

    logger.info(f"Agent 成长完成: {summary}")
    return {
        "summary": summary,
        "auto_actions": auto_actions,
        "suggestions": suggestions,
        "insights": stored_insights,
    }


def get_growth_reports(limit: int = 30) -> list[dict]:
    """获取成长报告列表"""
    db = _get_growth_db()
    rows = db.execute("SELECT * FROM growth_reports ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    db.close()
    results = []
    for r in rows:
        item = dict(r)
        item["suggestions"] = json.loads(item["suggestions"]) if item["suggestions"] else []
        item["auto_executed"] = json.loads(item["auto_executed"]) if item["auto_executed"] else []
        item["insights"] = json.loads(item["insights"]) if item["insights"] else {}
        results.append(item)
    return results


def confirm_suggestion(report_id: int, index: int) -> str:
    """确认执行🟡级建议"""
    db = _get_growth_db()
    row = db.execute("SELECT suggestions FROM growth_reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        db.close()
        return "记录不存在"

    suggestions = json.loads(row["suggestions"])
    if index >= len(suggestions):
        db.close()
        return "索引越界"

    s = suggestions[index]
    result = "未知操作"

    if s.get("action") == "disable_tool" and s.get("target") not in CORE_TOOLS:
        from .config import get_config_value, set_config_value
        disabled = get_config_value("disabled_tools", []) or []
        if s["target"] not in disabled:
            disabled.append(s["target"])
            set_config_value("disabled_tools", disabled)
            result = f"已禁用: {s['target']}"
    elif s.get("action") == "suggest_automation":
        result = f"建议已记录，可在定时任务中创建"
    elif s.get("action") == "investigate":
        result = "已标记为需人工排查"

    suggestions[index]["executed"] = True
    suggestions[index]["result"] = result
    db.execute("UPDATE growth_reports SET suggestions=? WHERE id=?",
               (json.dumps(suggestions, ensure_ascii=False), report_id))
    db.commit()
    db.close()
    return result


def should_grow() -> bool:
    """判断是否需要执行成长（距上次超过 24 小时）"""
    db = _get_growth_db()
    row = db.execute("SELECT date FROM growth_reports ORDER BY created_at DESC LIMIT 1").fetchone()
    db.close()
    if not row:
        return True
    try:
        last = datetime.strptime(row["date"], "%Y-%m-%d")
        return (datetime.now() - last).total_seconds() > 86400
    except (ValueError, TypeError):
        return True
