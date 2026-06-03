"""Agent 复盘 API 路由"""

import json
import sqlite3
from datetime import datetime, timedelta
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

    stats = get_tool_stats(days=7)
    today = datetime.now().strftime("%Y-%m-%d")

    # 分析：找出问题
    suggestions = []
    auto_executed = []

    failing = [s for s in stats if s.get("success_rate", 100) and s["success_rate"] < 70]
    for s in failing:
        suggestions.append({
            "level": "yellow",
            "text": f"工具 {s['tool_name']} 失败率 {100 - s['success_rate']:.0f}%，建议检查或禁用",
        })

    # 自动执行：清理统计（标记为已分析）
    if stats:
        auto_executed.append(f"分析了 {len(stats)} 个工具的近 7 天使用数据")

    summary = f"共分析 {len(stats)} 个工具，发现 {len(failing)} 个高失败率工具。"
    if not failing:
        summary += " 所有工具运行正常 ✅"

    # 写入复盘记录
    db = _get_db()
    db.execute(
        "INSERT INTO reviews (date, summary, suggestions, auto_executed) VALUES (?,?,?,?)",
        (today, summary, json.dumps(suggestions, ensure_ascii=False),
         json.dumps(auto_executed, ensure_ascii=False)),
    )
    db.commit()
    db.close()

    return {"success": True, "summary": summary, "suggestions": suggestions}
