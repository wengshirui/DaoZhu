import sqlite3
import os
from pathlib import Path

DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "prd.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        conn = get_db()
        conn.executescript(sql)
        conn.commit()
        conn.close()


def query(sql, params=None):
    conn = get_db()
    try:
        cur = conn.execute(sql, params or [])
        conn.commit()
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute(sql, params=None):
    conn = get_db()
    try:
        cur = conn.execute(sql, params or [])
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
