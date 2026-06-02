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
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
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
    # 迁移：确保 active 字段存在（旧数据库升级）
    _migrate_active_column(conn)
    conn.close()


def _migrate_active_column(conn: sqlite3.Connection):
    """迁移：为旧数据库添加 active 字段"""
    cursor = conn.execute("PRAGMA table_info(messages)")
    columns = [row[1] for row in cursor.fetchall()]
    if "active" not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_active ON messages(conversation_id, active)"
        )
        conn.commit()
    # 同时移除旧的 CHECK 约束（如果存在）— 通过重建表
    # 检测方法：尝试插入 tool_call 角色
    try:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES ('_test', 'tool_call', '_')"
        )
        conn.execute("DELETE FROM messages WHERE conversation_id = '_test'")
        conn.commit()
    except Exception:
        try:
            conn.executescript("""
                ALTER TABLE messages RENAME TO messages_old;
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
                INSERT INTO messages (id, conversation_id, role, content, active, created_at)
                    SELECT id, conversation_id, role, content, 1, created_at FROM messages_old;
                DROP TABLE messages_old;
                CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_messages_active ON messages(conversation_id, active);
            """)
        except Exception:
            pass


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
    """获取单个会话详情（仅含活跃消息）"""
    db = _get_db()
    conv = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not conv:
        db.close()
        return None

    messages = db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? AND active = 1 ORDER BY created_at",
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


def undo_messages(conv_id: str, n: int = 1) -> dict:
    """
    撤回最近 N 轮对话（一轮 = 一条 user + 对应的 assistant/tool_call 消息）
    返回: {"undone": int, "prefill": str} — 撤回的轮数 + 最后一条被撤回的用户消息文本
    """
    db = _get_db()

    # 获取活跃的 user 消息（从新到旧）
    user_msgs = db.execute(
        """SELECT id, content FROM messages
           WHERE conversation_id = ? AND active = 1 AND role = 'user'
           ORDER BY id DESC LIMIT ?""",
        (conv_id, n),
    ).fetchall()

    if not user_msgs:
        db.close()
        return {"undone": 0, "prefill": ""}

    # 最早要撤回的 user 消息 id（从这条开始往后全部软删除）
    oldest_user_id = user_msgs[-1]["id"]
    prefill_text = user_msgs[0]["content"]  # 最近一条用户消息（回填到输入框）

    # 软删除：从 oldest_user_id 开始的所有消息
    cursor = db.execute(
        """UPDATE messages SET active = 0
           WHERE conversation_id = ? AND active = 1 AND id >= ?""",
        (conv_id, oldest_user_id),
    )
    undone_count = cursor.rowcount
    db.commit()
    db.close()

    return {"undone": undone_count, "prefill": prefill_text}
