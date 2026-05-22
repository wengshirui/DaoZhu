"""Database manager — singleton access to master and accounting databases.

Provides a central point to get/switch database connections.
"""

import uuid
from datetime import date
from pathlib import Path
from typing import Optional

from accobot.db.master import MasterDB
from accobot.db.accounting import AccountingDB
from accobot.db.templates import init_accounts, init_periods
from accobot.config import get_data_dir


class DBManager:
    """Manages database connections for the application."""

    _instance: Optional["DBManager"] = None

    def __init__(self):
        self._master: Optional[MasterDB] = None
        self._accounting: Optional[AccountingDB] = None
        self._current_company_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "DBManager":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        if cls._instance:
            cls._instance.close()
        cls._instance = None

    @property
    def master(self) -> MasterDB:
        """Get the master database connection."""
        if self._master is None:
            self._master = MasterDB()
        return self._master

    @property
    def accounting(self) -> Optional[AccountingDB]:
        """Get the current accounting database connection."""
        if self._accounting is None:
            company_id = self.current_company_id
            if company_id:
                self._accounting = AccountingDB(company_id)
        return self._accounting

    @property
    def current_company_id(self) -> Optional[str]:
        """Get the current active company ID."""
        if self._current_company_id is None:
            self._current_company_id = self.master.get_current_company_id()
        return self._current_company_id

    def switch_company(self, company_id: str) -> bool:
        """Switch to a different company."""
        company = self.master.get_company(company_id)
        if not company:
            return False
        # Close current accounting db
        if self._accounting:
            self._accounting.close()
            self._accounting = None
        # Switch
        self.master.set_current_company_id(company_id)
        self._current_company_id = company_id
        # Open accounting db from company folder
        data_dir = get_data_dir()
        company_dir = data_dir / f"company_{company_id}"
        db_path = company_dir / "accounting.db"
        # Fallback to old flat structure if folder doesn't exist
        if not db_path.exists():
            db_path = data_dir / f"accounting_{company_id}.db"
        self._accounting = AccountingDB(company_id, db_path=db_path)
        return True

    def create_company(
        self,
        name: str,
        industry: str = "",
        taxpayer_type: str = "small_scale",
        accounting_standard: str = "small_enterprise",
    ) -> dict:
        """Create a new company with initialized accounts, periods, and folder structure."""
        company_id = uuid.uuid4().hex[:8]
        data_dir = get_data_dir()

        # Create company folder structure
        company_dir = data_dir / f"company_{company_id}"
        company_dir.mkdir(parents=True, exist_ok=True)
        (company_dir / "exports").mkdir(exist_ok=True)

        # Create documents folders for current year (原始单据按月归档)
        documents_dir = company_dir / "documents"
        documents_dir.mkdir(exist_ok=True)
        current_year = date.today().year
        for month in range(1, 13):
            (documents_dir / f"{current_year}-{month:02d}").mkdir(exist_ok=True)

        # Create in master db
        company = self.master.create_company(
            company_id=company_id,
            name=name,
            industry=industry,
            taxpayer_type=taxpayer_type,
            accounting_standard=accounting_standard,
        )

        # Initialize accounting db inside company folder
        db_path = company_dir / "accounting.db"
        acc_db = AccountingDB(company_id, db_path=db_path)
        account_count = init_accounts(acc_db, accounting_standard)
        period_count = init_periods(acc_db, current_year)
        acc_db.close()

        # Generate standard documents (REQ-023)
        from accobot.db.standards import generate_standard_docs
        generate_standard_docs(company_dir, accounting_standard)

        # Auto-switch to new company
        self.switch_company(company_id)

        return {
            **company,
            "accounts_initialized": account_count,
            "periods_initialized": period_count,
            "folder": str(company_dir),
        }

    def get_company_dir(self, company_id: str = None) -> Optional[Path]:
        """Get the folder path for a company."""
        cid = company_id or self.current_company_id
        if not cid:
            return None
        data_dir = get_data_dir()
        company_dir = data_dir / f"company_{cid}"
        if company_dir.exists():
            return company_dir
        return None

    def delete_company(self, company_id: str, confirm_name: str = "") -> dict:
        """Delete a company. Requires confirm_name to match the company name.

        Returns {"success": True/False, "error": "..."}.
        This is a destructive operation — removes the company folder and all data.
        """
        import shutil

        company = self.master.get_company(company_id)
        if not company:
            return {"success": False, "error": "账套不存在"}

        # Verify confirmation name matches
        if confirm_name != company["name"]:
            return {"success": False, "error": "公司名称不匹配，删除取消"}

        # If this is the current company, disconnect
        if self._current_company_id == company_id:
            if self._accounting:
                self._accounting.close()
                self._accounting = None
            self._current_company_id = None

        # Soft-delete in master db
        self.master.delete_company(company_id)

        # Remove company folder
        data_dir = get_data_dir()
        company_dir = data_dir / f"company_{company_id}"
        if company_dir.exists():
            shutil.rmtree(company_dir, ignore_errors=True)

        return {"success": True}

    def close(self):
        """Close all database connections."""
        if self._accounting:
            self._accounting.close()
            self._accounting = None
        if self._master:
            self._master.close()
            self._master = None
        self._current_company_id = None
