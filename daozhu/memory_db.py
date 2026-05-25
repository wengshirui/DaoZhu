"""
岛主 DaoZhu — 记忆系统存储层
三层记忆: 用户画像 / 知识库 / Skill 使用追踪
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import PLATFORM_ROOT

MEMORY_DB_PATH = PLATFORM_ROOT / "memory.db"

SCHEMA = """
-- === 用户画像（Layer 2）===
-- 用途: 存储用户偏好、习惯，每次对话注入 system prompt
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    source TEXT DEFAULT 'auto',
    confidence REAL DEFAULT 0.8,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 知识条目（Layer 3）===
-- 用途: 长期知识存储，从对话中提取的经验和事实
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    source_conversation_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === Skill 使用记录 ===
-- 用途: 追踪 skill 调用频率、成功率
CREATE TABLE IF NOT EXISTS skill_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT NOT NULL,
    action TEXT NOT NULL,
    success INTEGER DEFAULT 1,
    duration_ms INTEGER,
    context TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === FTS5 全文搜索索引 ===
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title, content, keywords,
    content=knowledge, content_rowid=id
);

-- === 触发器: 同步 FTS 索引 ===
CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
    INSERT INTO knowledge_fts(rowid, title, content, keywords)
    VALUES (new.id, new.title, new.content, new.keywords);
END;

CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, keywords)
    VALUES ('delete', old.id, old.title, old.content, old.keywords);
END;

-- === 索引 ===
CREATE INDEX IF NOT EXISTS idx_profile_key ON user_profile(key);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_skill_usage_skill ON skill_usage(skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_usage_time ON skill_usage(created_at);
"""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(MEMORY_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_memory_db():
    """初始化记忆数据库"""
    conn = _get_db()
    conn.executescript(SCHEMA)
    conn.close()


# === 用户画像 ===

def set_profile(key: str, value: str, source: str = "auto", confidence: float = 0.8):
    """设置/更新用户画像条目"""
    db = _get_db()
    db.execute(
        """INSERT INTO user_profile (key, value, source, confidence, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET
             value=excluded.value, source=excluded.source,
             confidence=excluded.confidence, updated_at=excluded.updated_at""",
        (key, value, source, confidence, datetime.now().isoformat()),
    )
    db.commit()
    db.close()


def get_profile(key: str) -> Optional[str]:
    """获取单个画像值"""
    db = _get_db()
    row = db.execute("SELECT value FROM user_profile WHERE key = ?", (key,)).fetchone()
    db.close()
    return row["value"] if row else None


def get_all_profiles() -> list[dict]:
    """获取全部用户画像"""
    db = _get_db()
    rows = db.execute(
        "SELECT key, value, confidence FROM user_profile ORDER BY updated_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# === 知识库 ===

def add_knowledge(category: str, title: str, content: str,
                  keywords: str = "", conversation_id: str = None) -> int:
    """添加知识条目"""
    db = _get_db()
    cursor = db.execute(
        """INSERT INTO knowledge (category, title, content, keywords, source_conversation_id)
           VALUES (?, ?, ?, ?, ?)""",
        (category, title, content, keywords, conversation_id),
    )
    db.commit()
    row_id = cursor.lastrowid
    db.close()
    return row_id


def search_knowledge(query: str, limit: int = 5) -> list[dict]:
    """全文搜索知识库"""
    db = _get_db()
    rows = db.execute(
        """SELECT k.id, k.category, k.title, k.content, k.keywords, k.created_at
           FROM knowledge_fts fts
           JOIN knowledge k ON k.id = fts.rowid
           WHERE knowledge_fts MATCH ?
           ORDER BY rank
           LIMIT ?""",
        (query, limit),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_recent_knowledge(limit: int = 10) -> list[dict]:
    """获取最近的知识条目"""
    db = _get_db()
    rows = db.execute(
        "SELECT * FROM knowledge ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# === Skill 使用追踪 ===

def track_skill_usage(skill_id: str, action: str, success: bool = True,
                      duration_ms: int = 0, context: str = ""):
    """记录 skill 使用"""
    db = _get_db()
    db.execute(
        """INSERT INTO skill_usage (skill_id, action, success, duration_ms, context)
           VALUES (?, ?, ?, ?, ?)""",
        (skill_id, action, int(success), duration_ms, context),
    )
    db.commit()
    db.close()


def get_skill_stats() -> list[dict]:
    """获取 skill 使用统计"""
    db = _get_db()
    rows = db.execute(
        """SELECT skill_id,
                  COUNT(*) as total_calls,
                  SUM(success) as success_count,
                  ROUND(AVG(success) * 100, 1) as success_rate,
                  MAX(created_at) as last_used
           FROM skill_usage
           GROUP BY skill_id
           ORDER BY total_calls DESC"""
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_stale_skills(days: int = 30) -> list[dict]:
    """获取超过 N 天未使用的 skill"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    db = _get_db()
    rows = db.execute(
        """SELECT skill_id, MAX(created_at) as last_used, COUNT(*) as total_calls
           FROM skill_usage
           GROUP BY skill_id
           HAVING MAX(created_at) < ?
           ORDER BY last_used""",
        (cutoff,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]
