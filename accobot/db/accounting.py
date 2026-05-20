"""Accounting database — per-company financial data.

Each company gets its own SQLite file: accounting_{company_id}.db
Stores: accounts (chart of accounts), vouchers, journal entries, aux items, periods.
"""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from accobot.config import get_data_dir


ACCOUNTING_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    balance_direction TEXT NOT NULL DEFAULT 'debit',
    parent_code TEXT,
    is_leaf INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    aux_attributes TEXT DEFAULT '[]',
    extra TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS aux_items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    code TEXT,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    extra TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS periods (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS vouchers (
    id TEXT PRIMARY KEY,
    voucher_number TEXT,
    voucher_date TEXT NOT NULL,
    period_id TEXT,
    voucher_type TEXT DEFAULT 'transfer',
    summary TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at REAL NOT NULL,
    updated_at REAL,
    extra TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id TEXT NOT NULL REFERENCES vouchers(id),
    account_code TEXT NOT NULL REFERENCES accounts(code),
    summary TEXT,
    debit REAL NOT NULL DEFAULT 0,
    credit REAL NOT NULL DEFAULT 0,
    aux_data TEXT DEFAULT '{}',
    extra TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_entries_voucher ON entries(voucher_id);
CREATE INDEX IF NOT EXISTS idx_entries_account ON entries(account_code);
CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(voucher_date);
CREATE INDEX IF NOT EXISTS idx_vouchers_period ON vouchers(period_id);
CREATE INDEX IF NOT EXISTS idx_accounts_category ON accounts(category);
CREATE INDEX IF NOT EXISTS idx_accounts_parent ON accounts(parent_code);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id TEXT REFERENCES vouchers(id),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    mime_type TEXT DEFAULT '',
    uploaded_at REAL NOT NULL,
    extra TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_attachments_voucher ON attachments(voucher_id);
"""

SCHEMA_VERSION = 1


class AccountingDB:
    """SQLite-backed accounting database for a single company."""

    def __init__(self, company_id: str, db_path: Optional[Path] = None):
        self.company_id = company_id
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (data_dir / f"accounting_{company_id}.db")

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
            self._conn.executescript(ACCOUNTING_SCHEMA)
            cur = self._conn.execute("SELECT version FROM schema_version LIMIT 1")
            row = cur.fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
                )

    # =========================================================================
    # Chart of Accounts
    # =========================================================================

    def add_account(self, code: str, name: str, category: str,
                    balance_direction: str = "debit", parent_code: str = None,
                    is_leaf: bool = True, aux_attributes: str = "[]") -> Dict[str, Any]:
        """Add an account to the chart of accounts."""
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO accounts
                   (code, name, category, balance_direction, parent_code, is_leaf, aux_attributes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (code, name, category, balance_direction, parent_code, int(is_leaf), aux_attributes),
            )
        return {"code": code, "name": name, "category": category}

    def get_account(self, code: str) -> Optional[Dict[str, Any]]:
        """Get an account by code."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM accounts WHERE code = ?", (code,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_accounts(self, category: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """List accounts, optionally filtered by category."""
        with self._lock:
            sql = "SELECT * FROM accounts WHERE 1=1"
            params = []
            if active_only:
                sql += " AND is_active = 1"
            if category:
                sql += " AND category = ?"
                params.append(category)
            sql += " ORDER BY code"
            cur = self._conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def search_accounts(self, keyword: str) -> List[Dict[str, Any]]:
        """Search accounts by name or code."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM accounts WHERE (name LIKE ? OR code LIKE ?) AND is_active = 1 ORDER BY code",
                (f"%{keyword}%", f"%{keyword}%"),
            )
            return [dict(row) for row in cur.fetchall()]

    def count_accounts(self) -> int:
        """Return total number of active accounts."""
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM accounts WHERE is_active = 1")
            return cur.fetchone()[0]

    # =========================================================================
    # Periods
    # =========================================================================

    def add_period(self, year: int, month: int, start_date: str, end_date: str) -> Dict[str, Any]:
        """Add an accounting period."""
        period_id = f"{year}-{month:02d}"
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO periods (id, year, month, start_date, end_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (period_id, year, month, start_date, end_date),
            )
        return {"id": period_id, "year": year, "month": month}

    def get_current_period(self) -> Optional[Dict[str, Any]]:
        """Get the latest open period."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM periods WHERE status = 'open' ORDER BY year DESC, month DESC LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_periods(self) -> List[Dict[str, Any]]:
        """List all periods."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM periods ORDER BY year, month")
            return [dict(row) for row in cur.fetchall()]

    # =========================================================================
    # Vouchers
    # =========================================================================

    def create_voucher(self, voucher_id: str, voucher_date: str, summary: str = "",
                       voucher_type: str = "transfer", period_id: str = None) -> Dict[str, Any]:
        """Create a new voucher."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO vouchers (id, voucher_date, summary, voucher_type, period_id, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'draft', ?)""",
                (voucher_id, voucher_date, summary, voucher_type, period_id, time.time()),
            )
        return {"id": voucher_id, "date": voucher_date, "summary": summary, "status": "draft"}

    def add_entry(self, voucher_id: str, account_code: str, debit: float = 0,
                  credit: float = 0, summary: str = "", aux_data: str = "{}") -> int:
        """Add a journal entry line to a voucher."""
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO entries (voucher_id, account_code, summary, debit, credit, aux_data)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (voucher_id, account_code, summary, debit, credit, aux_data),
            )
            return cur.lastrowid

    def get_voucher_with_entries(self, voucher_id: str) -> Optional[Dict[str, Any]]:
        """Get a voucher with all its entries."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,))
            voucher = cur.fetchone()
            if not voucher:
                return None
            voucher_dict = dict(voucher)
            cur = self._conn.execute(
                "SELECT * FROM entries WHERE voucher_id = ? ORDER BY id", (voucher_id,)
            )
            voucher_dict["entries"] = [dict(row) for row in cur.fetchall()]
            return voucher_dict

    def list_vouchers(self, period_id: str = None, status: str = None,
                      limit: int = 50) -> List[Dict[str, Any]]:
        """List vouchers with optional filters."""
        with self._lock:
            sql = "SELECT * FROM vouchers WHERE 1=1"
            params = []
            if period_id:
                sql += " AND period_id = ?"
                params.append(period_id)
            if status:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY voucher_date DESC, created_at DESC LIMIT ?"
            params.append(limit)
            cur = self._conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def update_voucher_status(self, voucher_id: str, status: str) -> bool:
        """Update voucher status (draft -> reviewed -> posted)."""
        with self._lock:
            self._conn.execute(
                "UPDATE vouchers SET status = ?, updated_at = ? WHERE id = ?",
                (status, time.time(), voucher_id),
            )
            return True

    # =========================================================================
    # Ledger Queries
    # =========================================================================

    def get_account_balance(self, account_code: str) -> Dict[str, float]:
        """Get the current balance of an account."""
        with self._lock:
            cur = self._conn.execute(
                """SELECT COALESCE(SUM(debit), 0) as total_debit,
                          COALESCE(SUM(credit), 0) as total_credit
                   FROM entries e
                   JOIN vouchers v ON e.voucher_id = v.id
                   WHERE e.account_code = ? AND v.status = 'posted'""",
                (account_code,),
            )
            row = cur.fetchone()
            total_debit = row["total_debit"]
            total_credit = row["total_credit"]

            # Get balance direction
            acct = self._conn.execute(
                "SELECT balance_direction FROM accounts WHERE code = ?", (account_code,)
            ).fetchone()
            direction = acct["balance_direction"] if acct else "debit"

            if direction == "debit":
                balance = total_debit - total_credit
            else:
                balance = total_credit - total_debit

            return {
                "account_code": account_code,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "balance": balance,
                "direction": direction,
            }

    def get_account_details(self, account_code: str, period_id: str = None) -> List[Dict[str, Any]]:
        """Get detailed entries for an account."""
        with self._lock:
            sql = """SELECT e.*, v.voucher_date, v.voucher_number, v.summary as voucher_summary
                     FROM entries e
                     JOIN vouchers v ON e.voucher_id = v.id
                     WHERE e.account_code = ? AND v.status = 'posted'"""
            params = [account_code]
            if period_id:
                sql += " AND v.period_id = ?"
                params.append(period_id)
            sql += " ORDER BY v.voucher_date, v.created_at"
            cur = self._conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # =========================================================================
    # Attachments
    # =========================================================================

    def add_attachment(self, voucher_id: str, filename: str, file_path: str,
                       file_size: int = 0, mime_type: str = "") -> int:
        """Link a file attachment to a voucher."""
        import time as _time
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO attachments (voucher_id, filename, file_path, file_size, mime_type, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (voucher_id, filename, file_path, file_size, mime_type, _time.time()),
            )
            return cur.lastrowid

    def get_attachments(self, voucher_id: str) -> List[Dict[str, Any]]:
        """Get all attachments for a voucher."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM attachments WHERE voucher_id = ? ORDER BY uploaded_at",
                (voucher_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def delete_attachment(self, attachment_id: int) -> bool:
        """Delete an attachment record (does not delete the file)."""
        with self._lock:
            self._conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
            return True
