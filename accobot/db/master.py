"""Master database — global metadata (user profile, company list).

Stores:
- User profile and role
- Company (account set) list and metadata
- Current active company selection
"""

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from accobot.config import get_data_dir


MASTER_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    role TEXT,
    name TEXT,
    preferences TEXT
);

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    taxpayer_type TEXT,
    accounting_standard TEXT DEFAULT 'small_enterprise',
    db_file TEXT NOT NULL,
    created_at REAL NOT NULL,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

SCHEMA_VERSION = 1


class MasterDB:
    """SQLite-backed master database for global metadata."""

    def __init__(self, db_path: Optional[Path] = None):
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (data_dir / "master.db")

        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript(MASTER_SCHEMA)
            # Check version
            cur = self._conn.execute("SELECT version FROM schema_version LIMIT 1")
            row = cur.fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
                )

    # =========================================================================
    # User Profile
    # =========================================================================

    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Get the user profile."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM user_profile WHERE id = 'default'")
            row = cur.fetchone()
            return dict(row) if row else None

    def set_user_profile(self, role: str, name: str = "") -> None:
        """Set or update user profile."""
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO user_profile (id, role, name)
                   VALUES ('default', ?, ?)""",
                (role, name),
            )

    # =========================================================================
    # Company Management
    # =========================================================================

    def create_company(
        self,
        company_id: str,
        name: str,
        industry: str = "",
        taxpayer_type: str = "small_scale",
        accounting_standard: str = "small_enterprise",
    ) -> Dict[str, Any]:
        """Create a new company (account set)."""
        import time

        db_file = f"accounting_{company_id}.db"
        with self._lock:
            self._conn.execute(
                """INSERT INTO companies (id, name, industry, taxpayer_type,
                   accounting_standard, db_file, created_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
                (company_id, name, industry, taxpayer_type,
                 accounting_standard, db_file, time.time()),
            )
        return {
            "id": company_id,
            "name": name,
            "industry": industry,
            "taxpayer_type": taxpayer_type,
            "accounting_standard": accounting_standard,
            "db_file": db_file,
        }

    def list_companies(self) -> List[Dict[str, Any]]:
        """List all active companies."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM companies WHERE status = 'active' ORDER BY created_at DESC"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get a company by ID."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_company(self, company_id: str) -> bool:
        """Soft-delete a company (mark as archived)."""
        with self._lock:
            self._conn.execute(
                "UPDATE companies SET status = 'archived' WHERE id = ?", (company_id,)
            )
            return True

    # =========================================================================
    # App State (current company, etc.)
    # =========================================================================

    def get_current_company_id(self) -> Optional[str]:
        """Get the currently active company ID."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT value FROM app_state WHERE key = 'current_company'"
            )
            row = cur.fetchone()
            return row["value"] if row else None

    def set_current_company_id(self, company_id: str) -> None:
        """Set the currently active company."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES ('current_company', ?)",
                (company_id,),
            )

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
