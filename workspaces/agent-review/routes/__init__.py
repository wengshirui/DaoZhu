"""Agent 复盘 API 路由"""

import json
import sqlite3
from datetime import datetime, timedelta, timedelta
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

# 复盘数据存在工作区本地
DB_PATH = Path(__file__).parent.parent / "data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    suggestions TEXT DEFAULT '[]',
    auto_executed TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


@router.get("/reviews")
async def list_reviews():
    """获取复盘报告列表"""
    db = _get_db()
    rows = db.execute("SELECT * FROM reviews ORDER BY date DESC LIMIT 30").fetchall()
    db.close()
    results = []
    for r in rows:
        item = dict(r)
        item["suggestions"] = json.loads(item["suggestions"]) if item["suggestions"] else []
        item["auto_executed"] = json.loads(item["auto_executed"]) if item["auto_executed"] else []
        results.append(item)
    return {"reviews": results}


@router.get("/stats")
async def get_review_stats():
    """获取工具统计（复盘数据源）"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from daozhu.tool_log_db import get_tool_stats, get_stale_tools
    return {
        "tool_stats": get_tool_stats(days=7),
        "stale_tools": get_stale_tools(days=30),
    }


@router.post("/run")
async def trigger_review():
    """手动触发一次复盘"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from daozhu.tool_log_db import get_tool_stats
    from daozhu.memory_db import get_recent_knowledge

    stats = get_tool_stats(days=7)
    today = datetime.now().strftime("%Y-%m-%d")

    # 核心工具列表（永远不建议禁用）
    CORE_TOOLS = {
        "list_workspaces", "call_workspace_api", "start_workspace",
        "stop_workspace", "get_workspace_info", "list_templates",
        "create_from_template", "write_file", "read_file", "list_files",
    }

    # 已处理过的建议（避免重复）
    db = _get_db()
    recent_reviews = db.execute(
        "SELECT suggestions FROM reviews WHERE date >= date('now', '-7 days')"
    ).fetchall()
    already_suggested = set()
    for row in recent_reviews:
        for s in json.loads(row["suggestions"] or "[]"):
            if s.get("executed"):
                already_suggested.add(s.get("target", ""))

    # 分析：找出问题
    suggestions = []
    auto_executed = []

    failing = [s for s in stats if s.get("success_rate") is not None and s["success_rate"] < 70]
    for s in failing:
        tool_name = s["tool_name"]
        rate = s["success_rate"]
        call_count = s.get("call_count", 0)

        # 跳过已处理的
        if tool_name in already_suggested:
            continue

        # 分析具体失败原因（读取最近 5 条失败日志）
        import sqlite3 as _sqlite3
        chat_db = _sqlite3.connect(str(Path(__file__).parent.parent.parent.parent / "chat.db"))
        chat_db.row_factory = _sqlite3.Row
        errors = chat_db.execute(
            "SELECT error, args FROM tool_logs WHERE tool_name=? AND success=0 ORDER BY created_at DESC LIMIT 5",
            (tool_name,)
        ).fetchall()
        chat_db.close()

        # 归类错误原因
        error_reasons = [e["error"] or "" for e in errors]
        is_404 = all("404" in r for r in error_reasons if r)
        is_param_error = any("参数" in r or "missing" in r or "positional" in r for r in error_reasons)

        if tool_name in CORE_TOOLS:
            if is_404:
                suggestions.append({
                    "level": "yellow",
                    "text": f"核心工具 {tool_name} 频繁 404（AI 传了错误路径），建议在工具返回中提示可用路径",
                    "action": "investigate",
                    "target": tool_name,
                    "detail": "失败原因: AI 编造了不存在的 API 路径",
                    "executed": False,
                })
            elif is_param_error:
                suggestions.append({
                    "level": "yellow",
                    "text": f"核心工具 {tool_name} 参数错误频发，建议优化工具描述让 AI 更清楚参数格式",
                    "action": "investigate",
                    "target": tool_name,
                    "detail": "失败原因: 参数格式错误",
                    "executed": False,
                })
            else:
                suggestions.append({
                    "level": "red",
                    "text": f"核心工具 {tool_name} 失败率 {100 - rate:.0f}%（{call_count} 次调用），需人工排查",
                    "action": "investigate",
                    "target": tool_name,
                    "detail": f"错误样例: {error_reasons[0][:80] if error_reasons else '未知'}",
                    "executed": False,
                })
        else:
            # 非核心工具
            if is_404:
                suggestions.append({
                    "level": "yellow",
                    "text": f"工具 {tool_name} 频繁 404，可能是目标地址不可达",
                    "action": "investigate",
                    "target": tool_name,
                    "executed": False,
                })
            else:
                suggestions.append({
                    "level": "yellow",
                    "text": f"工具 {tool_name} 失败率 {100 - rate:.0f}%，建议检查或禁用",
                    "action": "disable_tool",
                    "target": tool_name,
                    "executed": False,
                })

    # 🟢 自动执行：清理过期知识（超过 60 天的 tool_failure 记录）
    try:
        old_knowledge = get_recent_knowledge(limit=50)
        expired = [k for k in old_knowledge
                   if k.get("category") == "tool_failure"
                   and k.get("created_at", "") < (datetime.now() - timedelta(days=60)).isoformat()]
        if expired:
            import sqlite3 as _sqlite3
            db_mem = _sqlite3.connect(str(Path(__file__).parent.parent.parent.parent / "memory.db"))
            for k in expired:
                db_mem.execute("DELETE FROM knowledge WHERE id=?", (k["id"],))
            db_mem.commit()
            db_mem.close()
            auto_executed.append(f"🟢 清理了 {len(expired)} 条超过 60 天的工具失败记录")
    except Exception:
        pass

    # 统计摘要
    if stats:
        auto_executed.append(f"分析了 {len(stats)} 个工具的近 7 天使用数据")

    summary = f"共分析 {len(stats)} 个工具，发现 {len(failing)} 个高失败率工具。"
    if not suggestions:
        summary += " 无需新的优化建议 ✅"
    elif all(s["level"] == "red" for s in suggestions):
        summary += " 均为核心工具，建议排查而非禁用。"

    # 写入复盘记录
    db.execute(
        "INSERT INTO reviews (date, summary, suggestions, auto_executed) VALUES (?,?,?,?)",
        (today, summary, json.dumps(suggestions, ensure_ascii=False),
         json.dumps(auto_executed, ensure_ascii=False)),
    )
    db.commit()
    db.close()

    return {"success": True, "summary": summary, "suggestions": suggestions}


@router.post("/suggestions/{review_id}/confirm")
async def confirm_suggestion(review_id: int, body: dict):
    """确认执行🟡级建议（AC4）"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    index = body.get("index", 0)
    db = _get_db()
    row = db.execute("SELECT suggestions FROM reviews WHERE id=?", (review_id,)).fetchone()
    if not row:
        db.close()
        from fastapi import HTTPException
        raise HTTPException(404, "复盘记录不存在")

    suggestions = json.loads(row["suggestions"])
    if index >= len(suggestions):
        db.close()
        from fastapi import HTTPException
        raise HTTPException(400, "建议索引越界")

    suggestion = suggestions[index]
    # 执行建议
    result = "未知操作"
    if suggestion.get("action") == "disable_tool":
        from daozhu.config import get_config_value, set_config_value
        disabled = get_config_value("disabled_tools", []) or []
        tool_name = suggestion.get("target", "")
        if tool_name and tool_name not in disabled:
            disabled.append(tool_name)
            set_config_value("disabled_tools", disabled)
            result = f"已禁用工具: {tool_name}"

    # 标记为已执行
    suggestions[index]["executed"] = True
    suggestions[index]["result"] = result
    db.execute("UPDATE reviews SET suggestions=? WHERE id=?",
               (json.dumps(suggestions, ensure_ascii=False), review_id))
    db.commit()
    db.close()

    return {"success": True, "result": result}
