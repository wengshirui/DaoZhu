import sqlite3
import os
from pathlib import Path

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "weather.db"

def get_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        return
    with get_db() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))

def save_search(city: str, country: str = "CN"):
    with get_db() as conn:
        conn.execute("INSERT INTO searches (city, country) VALUES (?, ?)", (city, country))

def get_recent_searches(limit: int = 5):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT city, country FROM searches ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"city": r["city"], "country": r["country"]} for r in rows]

def add_favorite(city: str, country: str = "CN"):
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO favorites (city, country) VALUES (?, ?)", (city, country))
            return True
        except sqlite3.IntegrityError:
            return False

def remove_favorite(city: str, country: str = "CN"):
    with get_db() as conn:
        conn.execute("DELETE FROM favorites WHERE city=? AND country=?", (city, country))

def get_favorites():
    with get_db() as conn:
        rows = conn.execute("SELECT city, country FROM favorites ORDER BY id").fetchall()
        return [{"city": r["city"], "country": r["country"]} for r in rows]

def is_favorite(city: str, country: str = "CN"):
    with get_db() as conn:
        r = conn.execute("SELECT 1 FROM favorites WHERE city=? AND country=?", (city, country)).fetchone()
        return r is not None
