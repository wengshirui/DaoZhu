"""
岛主 DaoZhu — 对话持久化（平台级 SQLite）
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import PLATFORM_ROOT

CHAT_DB_PATH = PLATFORM_ROOT / "chat.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '新对话',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
"""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_chat_db():
    """初始化对话数据库"""
    conn = _get_db()
    conn.executescript(SCHEMA)
    conn.close()


def create_conversation(title: str = "新对话") -> dict:
    """创建新会话"""
    conv_id = str(uuid.uuid4())[:8]
    db = _get_db()
    db.execute(
        "INSERT INTO conversations (id, title) VALUES (?, ?)",
        (conv_id, title),
    )
    db.commit()
    row = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    db.close()
    return dict(row)


def list_conversations(limit: int = 50) -> list[dict]:
    """获取会话列表"""
    db = _get_db()
    rows = db.execute(
        "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_conversation(conv_id: str) -> Optional[dict]:
    """获取单个会话详情（含消息）"""
    db = _get_db()
    conv = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not conv:
        db.close()
        return None

    messages = db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
        (conv_id,),
    ).fetchall()
    db.close()

    result = dict(conv)
    result["messages"] = [dict(m) for m in messages]
    return result


def delete_conversation(conv_id: str) -> bool:
    """删除会话"""
    db = _get_db()
    cursor = db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    db.commit()
    db.close()
    return cursor.rowcount > 0


def add_message(conv_id: str, role: str, content: str) -> dict:
    """添加消息到会话"""
    db = _get_db()
    cursor = db.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conv_id, role, content),
    )
    # 更新会话时间和标题
    db.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), conv_id),
    )
    db.commit()
    msg = db.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    db.close()
    return dict(msg)


def update_conversation_title(conv_id: str, title: str):
    """更新会话标题"""
    db = _get_db()
    db.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
    db.commit()
    db.close()
