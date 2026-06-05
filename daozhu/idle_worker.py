"""
岛主 DaoZhu — AI 空闲自主工作引擎（#073 Phase 3）
职责：检测用户空闲 → AI 自主决策执行任务 → 生成工作汇报
思想基石：用户是谁 → 他想干什么 → 怎么帮他更好地实现
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import PLATFORM_ROOT, get_config_value

logger = logging.getLogger(__name__)

IDLE_DB_PATH = PLATFORM_ROOT / "idle_work.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    detail TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS idle_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,
    tasks_executed TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    shown INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(created_at);
"""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(IDLE_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


# === 交互时间追踪 ===

_last_interaction: Optional[datetime] = None


def record_interaction(event_type: str = "api_call", detail: str = ""):
    """记录一次用户交互（AC5）"""
    global _last_interaction
    _last_interaction = datetime.now()
    # 不每次都写 DB，只在内存中更新（高频操作）


def get_last_interaction() -> datetime:
    """获取最后交互时间"""
    global _last_interaction
    if _last_interaction:
        return _last_interaction
    # 首次启动，从 DB 读最后一条
    try:
        db = _get_db()
        row = db.execute(
            "SELECT created_at FROM activity_log ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        db.close()
        if row:
            _last_interaction = datetime.fromisoformat(row["created_at"])
            return _last_interaction
    except Exception:
        pass
    # 完全没有记录，用启动时间
    _last_interaction = datetime.now()
    return _last_interaction


def get_idle_minutes() -> float:
    """获取当前空闲分钟数"""
    last = get_last_interaction()
    return (datetime.now() - last).total_seconds() / 60


# === 空闲检测 + 任务执行 ===

_last_idle_run: Optional[datetime] = None
COOLDOWN_HOURS = 4  # 冷却时间（AC12）


async def check_and_run():
    """
    定时调用（每分钟）：检测空闲 → 执行自主任务。
    由 scheduler tick 调用。
    """
    global _last_idle_run

    # 检查开关（AC13）
    enabled = get_config_value("greeting.enabled", True)
    if not enabled:
        return

    # 获取阈值（AC10）
    threshold_hours = get_config_value("greeting.idle_threshold_hours", 2)
    idle_mins = get_idle_minutes()

    if idle_mins < threshold_hours * 60:
        return  # 还没空闲够

    # 冷却检查（AC12）
    if _last_idle_run:
        since_last = (datetime.now() - _last_idle_run).total_seconds() / 3600
        if since_last < COOLDOWN_HOURS:
            return  # 冷却期内

    # 执行自主任务
    logger.info(f"用户空闲 {idle_mins:.0f} 分钟，开始自主工作...")
    _last_idle_run = datetime.now()

    tasks_done = await _run_idle_tasks()

    if tasks_done:
        # 存储汇报（AC11）
        _save_report(tasks_done)
        logger.info(f"自主工作完成: {len(tasks_done)} 项任务")


# === 自主任务执行（AC6, AC7）===

async def _run_idle_tasks() -> list[dict]:
    """AI 自主决策并执行任务"""
    tasks_done = []

    # 任务 1：对话复盘总结
    try:
        summary = await _task_conversation_recap()
        if summary:
            tasks_done.append({"type": "对话复盘", "result": summary})
    except Exception as e:
        logger.warning(f"对话复盘失败: {e}")

    # 任务 2：待办到期检查
    try:
        todo_result = await _task_check_todos()
        if todo_result:
            tasks_done.append({"type": "待办检查", "result": todo_result})
    except Exception as e:
        logger.warning(f"待办检查失败: {e}")

    # 任务 3：撤回分析（AC9）
    try:
        undo_result = _task_analyze_undos()
        if undo_result:
            tasks_done.append({"type": "撤回分析", "result": undo_result})
    except Exception as e:
        logger.warning(f"撤回分析失败: {e}")

    return tasks_done


async def _task_conversation_recap() -> Optional[str]:
    """对话复盘：总结最近的对话内容"""
    from .chat_db import list_conversations, get_conversation

    convs = list_conversations(limit=3)
    if not convs:
        return None

    # 取最近对话的内容
    recent_msgs = []
    for conv in convs[:2]:
        full = get_conversation(conv["id"])
        if full and full.get("messages"):
            for msg in full["messages"][-3:]:
                if msg["role"] == "user":
                    content = (msg.get("content") or "")[:80]
                    if content:
                        recent_msgs.append(content)

    if not recent_msgs:
        return None

    # 调 LLM 做简短复盘
    from .chat_service import call_llm_simple
    prompt = f"""总结用户最近的关注点和未完成事项，用 2-3 句话概括。
不要用"主人/您"等敬语。直接输出总结，不要解释。

用户最近说的话：
{chr(10).join('- ' + m for m in recent_msgs[:6])}

简短总结："""

    result = await call_llm_simple(prompt, max_tokens=120)
    return result.strip() if result else None


async def _task_check_todos() -> Optional[str]:
    """检查待办到期情况"""
    import httpx
    from datetime import date

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:7801/api/tasks/", params={"today": "true"})
            if resp.status_code != 200:
                return None
            data = resp.json()
            tasks = data.get("tasks", [])
            active = [t for t in tasks if t.get("status") != "done"]
            overdue = [t for t in active if t.get("due_date") and t["due_date"] <= date.today().isoformat()]

            if overdue:
                names = "、".join(t["title"][:15] for t in overdue[:3])
                return f"{len(overdue)} 个待办已到期：{names}"
            elif active:
                return f"今天有 {len(active)} 个待办待处理"
            else:
                return "今天的待办都完成了"
    except Exception:
        return None


def _task_analyze_undos() -> Optional[str]:
    """分析撤回模式（AC9）"""
    try:
        chat_conn = sqlite3.connect(str(PLATFORM_ROOT / "chat.db"))
        chat_conn.row_factory = sqlite3.Row
        # 统计最近 7 天的撤回
        count = chat_conn.execute(
            "SELECT COUNT(*) FROM messages WHERE active=0 AND role='assistant' "
            "AND created_at > datetime('now', '-7 days', 'localtime')"
        ).fetchone()[0]
        chat_conn.close()

        if count > 0:
            return f"近 7 天有 {count} 次回答被撤回，需要优化回答质量"
        return None
    except Exception:
        return None


# === 汇报存储与读取 ===

def _save_report(tasks: list[dict]):
    """保存工作汇报"""
    summary_parts = [t["result"] for t in tasks if t.get("result")]
    summary = " | ".join(summary_parts) if summary_parts else "无特别发现"

    db = _get_db()
    db.execute(
        "INSERT INTO idle_reports (summary, tasks_executed) VALUES (?, ?)",
        (summary, json.dumps(tasks, ensure_ascii=False)),
    )
    db.commit()
    db.close()


def get_pending_report() -> Optional[dict]:
    """获取未展示的汇报（供 greeting API 调用）（AC8）"""
    db = _get_db()
    row = db.execute(
        "SELECT * FROM idle_reports WHERE shown=0 ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if row:
        result = dict(row)
        result["tasks_executed"] = json.loads(result["tasks_executed"])
        # 标记已展示
        db.execute("UPDATE idle_reports SET shown=1 WHERE id=?", (row["id"],))
        db.commit()
    else:
        result = None
    db.close()
    return result


def get_report_history(limit: int = 10) -> list[dict]:
    """获取汇报历史（供 agent-review 工作区展示）"""
    db = _get_db()
    rows = db.execute(
        "SELECT * FROM idle_reports ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    db.close()
    results = []
    for r in rows:
        item = dict(r)
        item["tasks_executed"] = json.loads(item["tasks_executed"])
        results.append(item)
    return results
