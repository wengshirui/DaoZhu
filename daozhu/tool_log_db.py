"""
岛主 DaoZhu — 工具调用日志持久化
记录每次工具调用的参数、结果、耗时，供后续分析优化。
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .config import PLATFORM_ROOT

TOOL_LOG_DB = PLATFORM_ROOT / "chat.db"  # 复用 chat.db

TOOL_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    tool_name TEXT NOT NULL,
    args TEXT DEFAULT '{}',
    result TEXT DEFAULT '',
    success INTEGER DEFAULT 1,
    duration_ms INTEGER DEFAULT 0,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tool_logs_name ON tool_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_logs_time ON tool_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_tool_logs_conv ON tool_logs(conversation_id);
"""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(TOOL_LOG_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_tool_log_db():
    """初始化工具日志表"""
    conn = _get_db()
    conn.executescript(TOOL_LOG_SCHEMA)
    conn.close()


def log_tool_call(
    tool_name: str,
    args: dict,
    result: str,
    success: bool,
    duration_ms: int,
    conversation_id: str = None,
    error: str = None,
):
    """记录一次工具调用"""
    db = _get_db()
    db.execute(
        """INSERT INTO tool_logs
           (conversation_id, tool_name, args, result, success, duration_ms, error)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            conversation_id,
            tool_name,
            json.dumps(args, ensure_ascii=False)[:2000],
            result[:5000] if result else "",
            1 if success else 0,
            duration_ms,
            error[:500] if error else None,
        ),
    )
    db.commit()
    db.close()


def get_tool_stats(days: int = 30) -> list[dict]:
    """获取最近 N 天的工具使用统计"""
    db = _get_db()
    rows = db.execute(
        """SELECT tool_name,
                  COUNT(*) as call_count,
                  SUM(success) as success_count,
                  AVG(duration_ms) as avg_duration_ms
           FROM tool_logs
           WHERE created_at > datetime('now', ?)
           GROUP BY tool_name
           ORDER BY call_count DESC""",
        (f"-{days} days",),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def cleanup_old_logs(days: int = 90):
    """清理超过 N 天的日志"""
    db = _get_db()
    db.execute(
        "DELETE FROM tool_logs WHERE created_at < datetime('now', ?)",
        (f"-{days} days",),
    )
    db.commit()
    db.close()
