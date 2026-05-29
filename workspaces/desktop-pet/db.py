"""数据库工具"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
