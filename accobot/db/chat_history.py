"""Chat history store — SQLite-backed conversation persistence.

Stores chat sessions and messages for the Web UI history panel.
"""

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from accobot.config import get_data_dir


CHAT_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '新对话',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    message_count INTEGER DEFAULT 0,
    company_id TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    tool_calls TEXT DEFAULT '',
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);
"""


class ChatHistoryDB:
    """SQLite-backed chat history."""

    def __init__(self, db_path: Optional[Path] = None):
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (data_dir / "chat_history.db")

        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript(CHAT_SCHEMA)

    # =========================================================================
    # Sessions
    # =========================================================================

    def create_session(self, title: str = "新对话", company_id: str = "") -> Dict[str, Any]:
        """Create a new chat session."""
        session_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at, company_id) VALUES (?, ?, ?, ?, ?)",
                (session_id, title, now, now, company_id),
            )
        return {"id": session_id, "title": title, "created_at": now, "message_count": 0}

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions ordered by last update."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_session_title(self, session_id: str, title: str) -> None:
        """Update session title (auto-generated from first message)."""
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, time.time(), session_id),
            )

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        with self._lock:
            self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # =========================================================================
    # Messages
    # =========================================================================

    def add_message(self, session_id: str, role: str, content: str,
                    tool_calls: str = "") -> int:
        """Add a message to a session."""
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, tool_calls, now),
            )
            # Update session
            self._conn.execute(
                "UPDATE sessions SET updated_at = ?, message_count = message_count + 1 WHERE id = ?",
                (now, session_id),
            )
            return cur.lastrowid

    def get_messages(self, session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Get messages for a session."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
