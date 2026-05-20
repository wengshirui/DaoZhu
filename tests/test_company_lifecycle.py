"""Tests for company lifecycle: create (with documents folder), switch, delete."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from accobot.db.manager import DBManager


@pytest.fixture(autouse=True)
def isolated_env(tmp_path):
    """Isolate each test with a fresh temp directory and DBManager."""
    with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path)}):
        DBManager.reset()
        yield tmp_path
        DBManager.reset()


class TestCompanyCreate:
    def test_creates_folder_structure(self, isolated_env):
        """Creating a company creates the correct folder structure."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        company_id = result["id"]

        company_dir = isolated_env / "data" / f"company_{company_id}"
        assert company_dir.exists()
        assert (company_dir / "accounting.db").exists()
        assert (company_dir / "documents").exists()
        assert (company_dir / "exports").exists()

    def test_creates_monthly_document_folders(self, isolated_env):
        """Documents folder has 12 monthly subfolders for current year."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        company_id = result["id"]

        from datetime import date
        year = date.today().year
        docs_dir = isolated_env / "data" / f"company_{company_id}" / "documents"

        for month in range(1, 13):
            folder = docs_dir / f"{year}-{month:02d}"
            assert folder.exists(), f"Missing folder: {folder}"

    def test_folder_named_documents_not_vouchers(self, isolated_env):
        """Folder is named 'documents' (原始单据), not 'vouchers' (凭证)."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        company_id = result["id"]

        company_dir = isolated_env / "data" / f"company_{company_id}"
        assert (company_dir / "documents").exists()
        assert not (company_dir / "vouchers").exists()

    def test_auto_switches_to_new_company(self, isolated_env):
        """After creation, the new company becomes the active one."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        assert mgr.current_company_id == result["id"]


class TestCompanyDelete:
    def test_delete_requires_matching_name(self, isolated_env):
        """Delete fails if confirm_name doesn't match."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        company_id = result["id"]

        delete_result = mgr.delete_company(company_id, "错误名称")
        assert delete_result["success"] is False
        assert "不匹配" in delete_result["error"]

        # Company should still exist
        assert mgr.master.get_company(company_id) is not None

    def test_delete_with_correct_name_succeeds(self, isolated_env):
        """Delete succeeds when confirm_name matches."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        company_id = result["id"]

        delete_result = mgr.delete_company(company_id, "测试公司")
        assert delete_result["success"] is True

        # Company folder should be removed
        company_dir = isolated_env / "data" / f"company_{company_id}"
        assert not company_dir.exists()

    def test_delete_removes_from_master_db(self, isolated_env):
        """Deleted company no longer appears in list."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        company_id = result["id"]

        mgr.delete_company(company_id, "测试公司")
        companies = mgr.master.list_companies()
        assert len(companies) == 0

    def test_delete_current_company_clears_selection(self, isolated_env):
        """Deleting the active company clears current_company_id."""
        mgr = DBManager.get_instance()
        result = mgr.create_company("测试公司")
        company_id = result["id"]
        assert mgr.current_company_id == company_id

        mgr.delete_company(company_id, "测试公司")
        assert mgr._current_company_id is None

    def test_delete_nonexistent_company(self, isolated_env):
        """Deleting a non-existent company returns error."""
        mgr = DBManager.get_instance()
        result = mgr.delete_company("nonexistent", "whatever")
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestCompanySwitch:
    def test_switch_updates_accounting_db(self, isolated_env):
        """Switching company changes the accounting db connection."""
        mgr = DBManager.get_instance()
        r1 = mgr.create_company("公司A")
        r2 = mgr.create_company("公司B")

        # Currently on 公司B (auto-switched after create)
        assert mgr.current_company_id == r2["id"]

        # Switch to 公司A
        mgr.switch_company(r1["id"])
        assert mgr.current_company_id == r1["id"]
        assert mgr.accounting is not None
