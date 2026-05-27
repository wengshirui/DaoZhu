"""
岛主 DaoZhu — 配置数据库
统一存储配置到 SQLite，替代 .env 路径依赖
"""

import sqlite3
from pathlib import Path
from typing import Optional

from .config import PLATFORM_ROOT

CONFIG_DB_PATH = PLATFORM_ROOT / "config.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    is_secret INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(CONFIG_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_config_db():
    """初始化配置数据库，从 .env 迁移"""
    db = _get_db()
    db.executescript(SCHEMA)

    # 从 .env 迁移（如果有）
    env_file = PLATFORM_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if value:
                db.execute(
                    "INSERT OR IGNORE INTO config (key, value, category, is_secret) VALUES (?, ?, 'secret', 1)",
                    (key, value),
                )
    db.commit()
    db.close()


def get_secret(key: str) -> Optional[str]:
    """获取密钥配置（API Key、Token 等）"""
    db = _get_db()
    row = db.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    db.close()
    if row:
        return row["value"]
    # 降级：从环境变量读取
    import os
    return os.environ.get(key)


def set_secret(key: str, value: str):
    """设置密钥配置"""
    db = _get_db()
    db.execute(
        """INSERT INTO config (key, value, category, is_secret, updated_at)
           VALUES (?, ?, 'secret', 1, datetime('now'))
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
        (key, value),
    )
    db.commit()
    db.close()


def delete_secret(key: str) -> bool:
    """删除密钥配置，返回是否实际删除了记录"""
    db = _get_db()
    cursor = db.execute("DELETE FROM config WHERE key = ? AND is_secret = 1", (key,))
    db.commit()
    deleted = cursor.rowcount > 0
    db.close()
    return deleted


def get_setting(key: str, default: str = "") -> str:
    """获取普通配置"""
    db = _get_db()
    row = db.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    db.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """设置普通配置"""
    db = _get_db()
    db.execute(
        """INSERT INTO config (key, value, category, is_secret, updated_at)
           VALUES (?, ?, 'general', 0, datetime('now'))
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
        (key, value),
    )
    db.commit()
    db.close()


def list_config(category: str = None) -> list[dict]:
    """列出配置（不返回 secret 的值）"""
    db = _get_db()
    if category:
        rows = db.execute("SELECT key, category, is_secret FROM config WHERE category = ?", (category,)).fetchall()
    else:
        rows = db.execute("SELECT key, category, is_secret FROM config").fetchall()
    db.close()
    return [dict(r) for r in rows]
