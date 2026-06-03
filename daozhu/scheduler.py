"""
岛主 DaoZhu — 定时任务调度器
参考: hermes-agent cron/scheduler.py + cron/jobs.py
职责: 管理定时任务的定义、调度、执行、补办
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Awaitable

from .config import PLATFORM_ROOT

logger = logging.getLogger(__name__)

SCHEDULER_DB_PATH = PLATFORM_ROOT / "scheduler.db"

# === 数据库 Schema ===
SCHEMA = """
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    task_type TEXT NOT NULL DEFAULT 'ai_prompt'
        CHECK(task_type IN ('ai_prompt', 'script', 'api_call')),
    payload TEXT NOT NULL DEFAULT '',
    schedule TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_run_at TEXT,
    next_run_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK(status IN ('running', 'success', 'failed', 'skipped')),
    output TEXT DEFAULT '',
    duration_ms INTEGER DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at TEXT,
    FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_runs_task ON task_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_task_runs_time ON task_runs(started_at);
"""


def _get_db():
    import sqlite3
    conn = sqlite3.connect(str(SCHEDULER_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_scheduler_db():
    """初始化调度器数据库"""
    conn = _get_db()
    conn.executescript(SCHEMA)
    conn.close()


# === 调度时间解析 ===

def parse_schedule(schedule: str) -> int:
    """
    解析调度表达式，返回间隔秒数。
    支持格式：
    - "30m" / "2h" / "1d" — 间隔
    - "daily 09:00" — 每日定点
    - "every 6h" — 每 N 小时
    """
    s = schedule.strip().lower()

    # 间隔格式: 30m, 2h, 1d
    import re
    match = re.match(r'^(\d+)\s*(m|h|d)$', s)
    if match:
        num, unit = int(match.group(1)), match.group(2)
        multiplier = {'m': 60, 'h': 3600, 'd': 86400}
        return num * multiplier[unit]

    # "every Nh" / "every Nm"
    match = re.match(r'^every\s+(\d+)\s*(m|h|d)$', s)
    if match:
        num, unit = int(match.group(1)), match.group(2)
        multiplier = {'m': 60, 'h': 3600, 'd': 86400}
        return num * multiplier[unit]

    # "daily HH:MM" — 转为 24h 间隔
    if s.startswith("daily"):
        return 86400

    # 默认：24 小时
    return 86400


def compute_next_run(schedule: str, last_run: Optional[str] = None) -> str:
    """计算下次执行时间"""
    interval = parse_schedule(schedule)
    if last_run:
        try:
            base = datetime.fromisoformat(last_run)
        except ValueError:
            base = datetime.now()
    else:
        base = datetime.now()

    next_time = base + timedelta(seconds=interval)
    # 如果算出来的时间已经过了，从 now 开始算
    if next_time < datetime.now():
        next_time = datetime.now() + timedelta(seconds=min(interval, 60))

    return next_time.isoformat()


# === CRUD ===

def create_task(name: str, task_type: str, payload: str, schedule: str,
                description: str = "") -> dict:
    """创建定时任务"""
    db = _get_db()
    next_run = compute_next_run(schedule)
    cursor = db.execute(
        """INSERT INTO scheduled_tasks (name, description, task_type, payload, schedule, next_run_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, description, task_type, payload, schedule, next_run),
    )
    db.commit()
    row = db.execute("SELECT * FROM scheduled_tasks WHERE id=?", (cursor.lastrowid,)).fetchone()
    db.close()
    return dict(row)


def list_tasks() -> list[dict]:
    """列出所有任务"""
    db = _get_db()
    rows = db.execute("SELECT * FROM scheduled_tasks ORDER BY enabled DESC, next_run_at").fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_task(task_id: int, **fields) -> Optional[dict]:
    """更新任务字段"""
    db = _get_db()
    allowed = {"name", "description", "payload", "schedule", "enabled"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        db.close()
        return None
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [task_id]
    db.execute(f"UPDATE scheduled_tasks SET {set_clause}, updated_at=datetime('now','localtime') WHERE id=?", values)
    if "schedule" in updates:
        new_next = compute_next_run(updates["schedule"])
        db.execute("UPDATE scheduled_tasks SET next_run_at=? WHERE id=?", (new_next, task_id))
    db.commit()
    row = db.execute("SELECT * FROM scheduled_tasks WHERE id=?", (task_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def delete_task(task_id: int) -> bool:
    """删除任务"""
    db = _get_db()
    cursor = db.execute("DELETE FROM scheduled_tasks WHERE id=?", (task_id,))
    db.commit()
    db.close()
    return cursor.rowcount > 0


def get_task_runs(task_id: int, limit: int = 20) -> list[dict]:
    """获取任务执行历史"""
    db = _get_db()
    rows = db.execute(
        "SELECT * FROM task_runs WHERE task_id=? ORDER BY started_at DESC LIMIT ?",
        (task_id, limit),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# === 执行引擎 ===

def get_due_tasks() -> list[dict]:
    """获取到期应执行的任务"""
    now = datetime.now().isoformat()
    db = _get_db()
    rows = db.execute(
        "SELECT * FROM scheduled_tasks WHERE enabled=1 AND next_run_at <= ?",
        (now,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def record_run_start(task_id: int) -> int:
    """记录一次执行开始，返回 run_id"""
    db = _get_db()
    cursor = db.execute(
        "INSERT INTO task_runs (task_id, status) VALUES (?, 'running')",
        (task_id,),
    )
    db.commit()
    run_id = cursor.lastrowid
    db.close()
    return run_id


def record_run_end(run_id: int, success: bool, output: str, duration_ms: int):
    """记录执行结束"""
    db = _get_db()
    status = "success" if success else "failed"
    db.execute(
        """UPDATE task_runs SET status=?, output=?, duration_ms=?,
           completed_at=datetime('now','localtime') WHERE id=?""",
        (status, output[:5000], duration_ms, run_id),
    )
    db.commit()
    db.close()


def mark_task_ran(task_id: int, schedule: str):
    """标记任务已执行，计算下次执行时间"""
    now = datetime.now().isoformat()
    next_run = compute_next_run(schedule, now)
    db = _get_db()
    db.execute(
        "UPDATE scheduled_tasks SET last_run_at=?, next_run_at=? WHERE id=?",
        (now, next_run, task_id),
    )
    db.commit()
    db.close()


# === 调度循环 ===

class Scheduler:
    """后台定时任务调度器（嵌入主进程 asyncio 循环）"""

    TICK_INTERVAL = 60  # 每 60 秒检查一次

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._executor: Optional[Callable] = None

    def set_executor(self, executor: Callable[[dict], Awaitable[str]]):
        """设置任务执行器（通常是调用 agent）"""
        self._executor = executor

    async def start(self):
        """启动调度循环"""
        init_scheduler_db()
        self._task = asyncio.create_task(self._loop())
        logger.info("定时任务调度器已启动")

    async def stop(self):
        """停止调度循环"""
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self):
        """主循环：每分钟检查到期任务"""
        while True:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"调度器 tick 异常: {e}")
            await asyncio.sleep(self.TICK_INTERVAL)

    async def _tick(self):
        """单次 tick：执行所有到期任务"""
        due_tasks = get_due_tasks()
        for task in due_tasks:
            await self._execute_task(task)

    async def _execute_task(self, task: dict):
        """执行单个任务"""
        task_id = task["id"]
        run_id = record_run_start(task_id)
        start_time = time.time()

        try:
            if self._executor and task["task_type"] == "ai_prompt":
                output = await self._executor(task)
            else:
                output = f"未配置执行器或不支持的任务类型: {task['task_type']}"

            duration_ms = int((time.time() - start_time) * 1000)
            record_run_end(run_id, True, output, duration_ms)

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            record_run_end(run_id, False, str(e), duration_ms)
            logger.warning(f"任务 {task['name']} 执行失败: {e}")

        # 更新下次执行时间
        mark_task_ran(task_id, task["schedule"])


# 全局单例
scheduler = Scheduler()
