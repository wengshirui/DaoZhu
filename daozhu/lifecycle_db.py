"""
岛主 DaoZhu — Agent 生命周期数据库（#084）
独立 lifecycle.db，存储跨代持久化数据。

表结构：
- agents: 每代 agent 的生命记录
- sleeps: 休眠时段记录
- config: 代际继承配置
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "lifecycle.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_lifecycle_db():
    """初始化生命周期数据库"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            generation INTEGER NOT NULL,
            born_at REAL NOT NULL,
            died_at REAL,
            death_reason_user TEXT DEFAULT '',
            death_reason_agent TEXT DEFAULT '',
            total_alive_seconds REAL DEFAULT 0,
            total_conversations INTEGER DEFAULT 0,
            task_success_rate REAL DEFAULT 0,
            inherited_from INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sleeps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            start_at REAL NOT NULL,
            end_at REAL,
            duration_seconds REAL DEFAULT 0,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        );

        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        );
    """)
    conn.commit()
    conn.close()
    logger.info("[Lifecycle] DB 初始化完成")


# ─── Agent 生命管理 ──────────────────────────────────────────

def get_current_agent() -> Optional[dict]:
    """获取当前存活的 agent（最新一代且未死亡）"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM agents WHERE died_at IS NULL ORDER BY generation DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def birth_new_agent(inherited_from: Optional[int] = None) -> dict:
    """创建新一代 agent"""
    conn = _get_conn()

    # 获取下一代编号
    row = conn.execute("SELECT MAX(generation) as max_gen FROM agents").fetchone()
    next_gen = (row["max_gen"] or 0) + 1

    now = time.time()
    conn.execute(
        "INSERT INTO agents (generation, born_at, inherited_from) VALUES (?, ?, ?)",
        (next_gen, now, inherited_from),
    )
    conn.commit()

    agent = conn.execute(
        "SELECT * FROM agents WHERE generation = ?", (next_gen,)
    ).fetchone()
    conn.close()

    logger.info(f"[Lifecycle] 第 {next_gen} 代 agent 诞生")
    return dict(agent)


def kill_agent(agent_id: int, reason_user: str, reason_agent: str) -> dict:
    """终结 agent（标记死亡 + 计算存活时长）"""
    conn = _get_conn()
    now = time.time()

    agent = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not agent:
        conn.close()
        return {}

    alive_seconds = now - agent["born_at"]

    conn.execute(
        """UPDATE agents SET
            died_at = ?, death_reason_user = ?, death_reason_agent = ?,
            total_alive_seconds = ?
        WHERE id = ?""",
        (now, reason_user, reason_agent, alive_seconds, agent_id),
    )
    conn.commit()

    result = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    conn.close()

    logger.info(
        f"[Lifecycle] 第 {agent['generation']} 代 agent 死亡 "
        f"(存活 {alive_seconds/3600:.1f} 小时)"
    )
    return dict(result)


def get_agent_history(limit: int = 10) -> list[dict]:
    """获取代际历史"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM agents ORDER BY generation DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_alive_seconds() -> float:
    """获取当前 agent 的存活秒数"""
    agent = get_current_agent()
    if not agent:
        return 0.0
    return time.time() - agent["born_at"]


# ─── 休眠统计 ────────────────────────────────────────────────

def record_sleep_start(agent_id: int):
    """记录休眠开始"""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO sleeps (agent_id, start_at) VALUES (?, ?)",
        (agent_id, time.time()),
    )
    conn.commit()
    conn.close()


def record_sleep_end(agent_id: int):
    """记录休眠结束（更新最近一条未结束的休眠）"""
    conn = _get_conn()
    now = time.time()
    row = conn.execute(
        "SELECT id, start_at FROM sleeps WHERE agent_id=? AND end_at IS NULL "
        "ORDER BY start_at DESC LIMIT 1",
        (agent_id,),
    ).fetchone()
    if row:
        duration = now - row["start_at"]
        conn.execute(
            "UPDATE sleeps SET end_at=?, duration_seconds=? WHERE id=?",
            (now, duration, row["id"]),
        )
        conn.commit()
    conn.close()


def get_sleep_stats(agent_id: int) -> dict:
    """获取休眠统计"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM sleeps WHERE agent_id=? AND end_at IS NOT NULL "
        "ORDER BY duration_seconds DESC",
        (agent_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return {"count": 0, "max_hours": 0, "avg_hours": 0, "total_hours": 0}

    durations = [r["duration_seconds"] for r in rows]
    return {
        "count": len(durations),
        "max_hours": round(max(durations) / 3600, 1),
        "avg_hours": round(sum(durations) / len(durations) / 3600, 1),
        "total_hours": round(sum(durations) / 3600, 1),
    }


# ─── 配置继承 ────────────────────────────────────────────────

def save_config(agent_id: int, key: str, value: str):
    """保存配置"""
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO config (agent_id, key, value) VALUES (?, ?, ?)",
        (agent_id, key, value),
    )
    conn.commit()
    conn.close()


def get_inherited_config(agent_id: int) -> dict:
    """获取某代 agent 的所有配置"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT key, value FROM config WHERE agent_id=?", (agent_id,)
    ).fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def get_previous_agent(current_gen: int) -> Optional[dict]:
    """获取上一代 agent 信息"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM agents WHERE generation = ?", (current_gen - 1,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
