"""Agent 成长系统 — API 路由"""

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

DB_PATH = Path(__file__).parent.parent / "data.db"
PLATFORM_ROOT = Path(__file__).parent.parent.parent.parent

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    suggestions TEXT DEFAULT '[]',
    auto_executed TEXT DEFAULT '[]',
    growth_insights TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 核心工具（永不建议禁用）
CORE_TOOLS = {
    "list_workspaces", "call_workspace_api", "start_workspace",
    "stop_workspace", "get_workspace_info", "list_templates",
    "create_from_template", "write_file", "read_file", "list_files",
}


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    # 迁移：确保 growth_insights 列存在
    try:
        conn.execute("SELECT growth_insights FROM reviews LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE reviews ADD COLUMN growth_insights TEXT DEFAULT '{}'")
    return conn


def _get_chat_db():
    return sqlite3.connect(str(PLATFORM_ROOT / "chat.db"))


def _get_memory_db():
    return sqlite3.connect(str(PLATFORM_ROOT / "memory.db"))


# === 成长分析引擎 ===

def _analyze_user_patterns(chat_conn) -> dict:
    """维度 1：分析用户对话模式"""
    chat_conn.row_factory = sqlite3.Row
    msgs = chat_conn.execute(
        "SELECT content, created_at FROM messages WHERE role='user' AND active=1 ORDER BY created_at DESC LIMIT 100"
    ).fetchall()

    if not msgs:
        return {"total_msgs": 0, "patterns": [], "peak_hour": None, "repeated": []}

    # 请求类型分类
    patterns = Counter()
    for msg in msgs:
        text = msg["content"] or ""
        if "工作区" in text or "建" in text or "创建" in text:
            patterns["工作区管理"] += 1
        elif "天气" in text or "查" in text or "搜" in text or "搜索" in text:
            patterns["信息查询"] += 1
        elif "待办" in text or "任务" in text or "记" in text:
            patterns["任务管理"] += 1
        elif "启动" in text or "打开" in text or "停止" in text:
            patterns["工作区操控"] += 1
        else:
            patterns["通用对话"] += 1

    # 时间分布
    hours = Counter()
    for msg in msgs:
        if msg["created_at"]:
            try:
                h = datetime.fromisoformat(msg["created_at"]).hour
                hours[h] += 1
            except (ValueError, TypeError):
                pass

    peak_hour = hours.most_common(1)[0][0] if hours else None

    # 重复请求检测
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


def _analyze_self_improvement(chat_conn) -> dict:
    """维度 2：自我优化空间"""
    chat_conn.row_factory = sqlite3.Row

    # 撤回分析
    undo_count = chat_conn.execute(
        "SELECT COUNT(*) FROM messages WHERE active=0 AND role='assistant'"
    ).fetchone()[0]
    total_assistant = chat_conn.execute(
        "SELECT COUNT(*) FROM messages WHERE role='assistant'"
    ).fetchone()[0]

    # 工具效率
    tool_stats = chat_conn.execute("""
        SELECT tool_name, COUNT(*) as calls, SUM(success) as ok,
               ROUND(AVG(duration_ms)) as avg_ms
        FROM tool_logs WHERE created_at > datetime('now', '-7 days')
        GROUP BY tool_name ORDER BY calls DESC
    """).fetchall()

    # 失败详情
    failing_tools = []
    for t in tool_stats:
        rate = (t["ok"] / t["calls"] * 100) if t["calls"] > 0 else 100
        if rate < 70:
            errors = chat_conn.execute(
                "SELECT error FROM tool_logs WHERE tool_name=? AND success=0 ORDER BY created_at DESC LIMIT 3",
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
        "tool_stats": [dict(t) for t in tool_stats],
        "failing_tools": failing_tools,
    }


def _analyze_proactive_opportunities(chat_conn, memory_conn) -> dict:
    """维度 3：主动服务机会"""
    memory_conn.row_factory = sqlite3.Row

    # 画像重复检测
    profiles = memory_conn.execute("SELECT id, key, value FROM user_profile").fetchall()
    profile_keys = Counter(p["key"] for p in profiles)
    duplicates = [(k, v) for k, v in profile_keys.items() if v > 1]

    # 知识库大小
    knowledge_count = memory_conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]

    return {
        "profile_count": len(profiles),
        "duplicate_profiles": duplicates,
        "knowledge_count": knowledge_count,
    }


# === 自动成长动作 ===

def _auto_grow(insights: dict, memory_conn) -> list[str]:
    """执行🟢级自动成长动作，返回执行记录"""
    actions = []
    memory_conn.row_factory = sqlite3.Row

    # 1. 合并重复画像
    duplicates = insights.get("proactive", {}).get("duplicate_profiles", [])
    if duplicates:
        for key, count in duplicates:
            # 保留最新的一条，删除旧的
            rows = memory_conn.execute(
                "SELECT id FROM user_profile WHERE key=? ORDER BY updated_at DESC",
                (key,)
            ).fetchall()
            if len(rows) > 1:
                old_ids = [r["id"] for r in rows[1:]]
                memory_conn.execute(
                    f"DELETE FROM user_profile WHERE id IN ({','.join('?' * len(old_ids))})",
                    old_ids
                )
                actions.append(f"🟢 合并重复画像「{key}」({count} → 1)")

    # 2. 从高频模式自动补充画像
    patterns = insights.get("user_patterns", {}).get("patterns", [])
    if patterns:
        top_pattern = patterns[0][0] if patterns else None
        if top_pattern:
            existing = memory_conn.execute(
                "SELECT value FROM user_profile WHERE key='主要用途'"
            ).fetchone()
            if not existing:
                memory_conn.execute(
                    """INSERT INTO user_profile (key, value, source, confidence, updated_at)
                       VALUES ('主要用途', ?, 'auto_growth', 0.7, datetime('now', 'localtime'))""",
                    (f"{top_pattern}（基于近期对话分析）",)
                )
                actions.append(f"🟢 自动记录画像: 主要用途 = {top_pattern}")

    # 3. 从使用时段补充画像
    peak = insights.get("user_patterns", {}).get("peak_hour")
    if peak is not None:
        existing = memory_conn.execute(
            "SELECT value FROM user_profile WHERE key='活跃时段'"
        ).fetchone()
        if not existing:
            memory_conn.execute(
                """INSERT INTO user_profile (key, value, source, confidence, updated_at)
                   VALUES ('活跃时段', ?, 'auto_growth', 0.6, datetime('now', 'localtime'))""",
                (f"主要在 {peak}:00 前后使用",)
            )
            actions.append(f"🟢 自动记录画像: 活跃时段 = {peak}:00")

    # 4. 清理过期的工具失败知识
    cutoff = (datetime.now() - timedelta(days=60)).isoformat()
    old_failures = memory_conn.execute(
        "SELECT id FROM knowledge WHERE category='tool_failure' AND created_at < ?",
        (cutoff,)
    ).fetchall()
    if old_failures:
        ids = [r["id"] for r in old_failures]
        memory_conn.execute(
            f"DELETE FROM knowledge WHERE id IN ({','.join('?' * len(ids))})", ids
        )
        actions.append(f"🟢 清理 {len(ids)} 条过期工具失败记录")

    memory_conn.commit()
    return actions


def _generate_suggestions(insights: dict) -> list[dict]:
    """基于分析结果生成建议"""
    suggestions = []

    # 从重复请求推断自动化机会
    repeated = insights.get("user_patterns", {}).get("repeated", [])
    for pattern, count in repeated[:3]:
        if count >= 3:
            suggestions.append({
                "level": "yellow",
                "text": f"用户重复请求「{pattern[:15]}...」{count} 次，建议创建定时任务自动化",
                "action": "suggest_automation",
                "target": pattern,
                "executed": False,
            })

    # 高失败率工具建议
    failing = insights.get("self_improvement", {}).get("failing_tools", [])
    for tool in failing:
        if tool["is_core"]:
            error_sample = tool["errors"][0] if tool["errors"] else "未知"
            suggestions.append({
                "level": "red",
                "text": f"核心工具 {tool['name']} 失败率 {100 - tool['rate']:.0f}%，原因: {error_sample}",
                "action": "investigate",
                "target": tool["name"],
                "executed": False,
            })
        else:
            suggestions.append({
                "level": "yellow",
                "text": f"工具 {tool['name']} 失败率 {100 - tool['rate']:.0f}%，建议检查或禁用",
                "action": "disable_tool",
                "target": tool["name"],
                "executed": False,
            })

    return suggestions


# === API 端点 ===

@router.get("/reviews")
async def list_reviews():
    """获取成长报告列表"""
    db = _get_db()
    rows = db.execute("SELECT * FROM reviews ORDER BY date DESC LIMIT 30").fetchall()
    db.close()
    results = []
    for r in rows:
        item = dict(r)
        item["suggestions"] = json.loads(item["suggestions"]) if item["suggestions"] else []
        item["auto_executed"] = json.loads(item["auto_executed"]) if item["auto_executed"] else []
        item["growth_insights"] = json.loads(item.get("growth_insights") or "{}") if item.get("growth_insights") else {}
        results.append(item)
    return {"reviews": results}


@router.get("/stats")
async def get_stats():
    """获取当前健康数据（不触发成长）"""
    import sys
    sys.path.insert(0, str(PLATFORM_ROOT))
    from daozhu.tool_log_db import get_tool_stats, get_stale_tools
    return {
        "tool_stats": get_tool_stats(days=7),
        "stale_tools": get_stale_tools(days=30),
    }


@router.post("/run")
async def trigger_growth():
    """触发一次成长分析（三维度）"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 连接数据库
    chat_conn = _get_chat_db()
    memory_conn = _get_memory_db()

    # 三维度分析
    user_patterns = _analyze_user_patterns(chat_conn)
    self_improvement = _analyze_self_improvement(chat_conn)
    proactive = _analyze_proactive_opportunities(chat_conn, memory_conn)

    insights = {
        "user_patterns": user_patterns,
        "self_improvement": self_improvement,
        "proactive": proactive,
    }

    # 🟢 自动执行成长动作
    auto_actions = _auto_grow(insights, memory_conn)

    # 生成建议
    suggestions = _generate_suggestions(insights)

    # 构建摘要
    parts = []
    parts.append(f"分析了 {user_patterns['total_msgs']} 条对话")
    if user_patterns["patterns"]:
        top = user_patterns["patterns"][0]
        parts.append(f"用户最常做: {top[0]}({top[1]}次)")
    if self_improvement["failing_tools"]:
        parts.append(f"{len(self_improvement['failing_tools'])} 个工具需关注")
    if user_patterns["repeated"]:
        parts.append(f"发现 {len(user_patterns['repeated'])} 个可自动化的重复模式")
    summary = "。".join(parts) + "。"

    # 保存
    db = _get_db()
    db.execute(
        """INSERT INTO reviews (date, summary, suggestions, auto_executed, growth_insights)
           VALUES (?,?,?,?,?)""",
        (today, summary,
         json.dumps(suggestions, ensure_ascii=False),
         json.dumps(auto_actions, ensure_ascii=False),
         json.dumps({
             "patterns": user_patterns["patterns"],
             "peak_hour": user_patterns["peak_hour"],
             "repeated_count": len(user_patterns["repeated"]),
             "undo_rate": self_improvement["undo_rate"],
             "profile_count": proactive["profile_count"],
         }, ensure_ascii=False)),
    )
    db.commit()
    db.close()

    chat_conn.close()
    memory_conn.close()

    return {
        "success": True,
        "summary": summary,
        "auto_actions": auto_actions,
        "suggestions": suggestions,
        "insights": {
            "top_pattern": user_patterns["patterns"][0] if user_patterns["patterns"] else None,
            "peak_hour": user_patterns["peak_hour"],
            "repeated": user_patterns["repeated"][:3],
            "undo_rate": self_improvement["undo_rate"],
        },
    }


@router.post("/suggestions/{review_id}/confirm")
async def confirm_suggestion(review_id: int, body: dict):
    """确认执行🟡级建议"""
    import sys
    sys.path.insert(0, str(PLATFORM_ROOT))

    index = body.get("index", 0)
    db = _get_db()
    row = db.execute("SELECT suggestions FROM reviews WHERE id=?", (review_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "记录不存在")

    suggestions = json.loads(row["suggestions"])
    if index >= len(suggestions):
        db.close()
        raise HTTPException(400, "索引越界")

    suggestion = suggestions[index]
    result = "未知操作"

    if suggestion.get("action") == "disable_tool":
        from daozhu.config import get_config_value, set_config_value
        disabled = get_config_value("disabled_tools", []) or []
        tool_name = suggestion.get("target", "")
        if tool_name and tool_name not in disabled and tool_name not in CORE_TOOLS:
            disabled.append(tool_name)
            set_config_value("disabled_tools", disabled)
            result = f"已禁用工具: {tool_name}"
        elif tool_name in CORE_TOOLS:
            result = f"拒绝: {tool_name} 是核心工具，不可禁用"
        else:
            result = f"{tool_name} 已经被禁用"

    elif suggestion.get("action") == "suggest_automation":
        result = f"建议已记录: 考虑为「{suggestion.get('target', '')[:15]}」创建定时任务"

    suggestions[index]["executed"] = True
    suggestions[index]["result"] = result
    db.execute("UPDATE reviews SET suggestions=? WHERE id=?",
               (json.dumps(suggestions, ensure_ascii=False), review_id))
    db.commit()
    db.close()

    return {"success": True, "result": result}
