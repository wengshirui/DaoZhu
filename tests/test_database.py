"""Tests for database modules."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from accobot.db.master import MasterDB
from accobot.db.accounting import AccountingDB
from accobot.db.templates import init_accounts, init_periods, load_template


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory."""
    with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path)}):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        yield data_dir


@pytest.fixture
def master_db(tmp_data_dir):
    db = MasterDB(db_path=tmp_data_dir / "master.db")
    yield db
    db.close()


@pytest.fixture
def accounting_db(tmp_data_dir):
    db = AccountingDB("test_company", db_path=tmp_data_dir / "accounting_test.db")
    yield db
    db.close()


# =========================================================================
# Master DB Tests
# =========================================================================

class TestMasterDB:
    def test_create_and_list_companies(self, master_db):
        master_db.create_company("c1", "测试公司", industry="餐饮")
        master_db.create_company("c2", "另一家公司", industry="电商")
        companies = master_db.list_companies()
        assert len(companies) == 2
        names = [c["name"] for c in companies]
        assert "测试公司" in names
        assert "另一家公司" in names

    def test_get_company(self, master_db):
        master_db.create_company("c1", "测试公司", taxpayer_type="general")
        company = master_db.get_company("c1")
        assert company["name"] == "测试公司"
        assert company["taxpayer_type"] == "general"

    def test_delete_company(self, master_db):
        master_db.create_company("c1", "测试公司")
        master_db.delete_company("c1")
        companies = master_db.list_companies()
        assert len(companies) == 0

    def test_current_company(self, master_db):
        assert master_db.get_current_company_id() is None
        master_db.create_company("c1", "测试公司")
        master_db.set_current_company_id("c1")
        assert master_db.get_current_company_id() == "c1"

    def test_user_profile(self, master_db):
        assert master_db.get_user_profile() is None
        master_db.set_user_profile("boss", "张老板")
        profile = master_db.get_user_profile()
        assert profile["role"] == "boss"
        assert profile["name"] == "张老板"


# =========================================================================
# Accounting DB Tests
# =========================================================================

class TestAccountingDB:
    def test_add_and_get_account(self, accounting_db):
        accounting_db.add_account("1001", "库存现金", "asset", "debit")
        acct = accounting_db.get_account("1001")
        assert acct["name"] == "库存现金"
        assert acct["category"] == "asset"

    def test_list_accounts_by_category(self, accounting_db):
        accounting_db.add_account("1001", "库存现金", "asset", "debit")
        accounting_db.add_account("2001", "短期借款", "liability", "credit")
        assets = accounting_db.list_accounts(category="asset")
        assert len(assets) == 1
        assert assets[0]["code"] == "1001"

    def test_search_accounts(self, accounting_db):
        accounting_db.add_account("1001", "库存现金", "asset", "debit")
        accounting_db.add_account("1002", "银行存款", "asset", "debit")
        results = accounting_db.search_accounts("银行")
        assert len(results) == 1
        assert results[0]["name"] == "银行存款"

    def test_create_voucher_and_entries(self, accounting_db):
        accounting_db.add_account("5602", "管理费用", "expense", "debit")
        accounting_db.add_account("1002", "银行存款", "asset", "debit")

        accounting_db.create_voucher("V001", "2026-05-20", summary="付房租")
        accounting_db.add_entry("V001", "5602", debit=5000, summary="房租")
        accounting_db.add_entry("V001", "1002", credit=5000, summary="房租")

        voucher = accounting_db.get_voucher_with_entries("V001")
        assert voucher["summary"] == "付房租"
        assert len(voucher["entries"]) == 2
        assert voucher["entries"][0]["debit"] == 5000
        assert voucher["entries"][1]["credit"] == 5000

    def test_account_balance(self, accounting_db):
        accounting_db.add_account("1002", "银行存款", "asset", "debit")
        accounting_db.create_voucher("V001", "2026-05-20")
        accounting_db.add_entry("V001", "1002", debit=10000)
        accounting_db.update_voucher_status("V001", "posted")

        accounting_db.create_voucher("V002", "2026-05-21")
        accounting_db.add_entry("V002", "1002", credit=3000)
        accounting_db.update_voucher_status("V002", "posted")

        balance = accounting_db.get_account_balance("1002")
        assert balance["balance"] == 7000  # 10000 - 3000
        assert balance["direction"] == "debit"

    def test_periods(self, accounting_db):
        accounting_db.add_period(2026, 5, "2026-05-01", "2026-05-31")
        period = accounting_db.get_current_period()
        assert period["year"] == 2026
        assert period["month"] == 5


# =========================================================================
# Template Tests
# =========================================================================

class TestTemplates:
    def test_load_template(self):
        template = load_template("small_enterprise")
        assert len(template) > 50  # Should have many accounts
        # Check first account
        assert template[0][0] == "1001"  # code
        assert template[0][1] == "库存现金"  # name

    def test_init_accounts(self, accounting_db):
        count = init_accounts(accounting_db, "small_enterprise")
        assert count > 50
        assert accounting_db.count_accounts() > 50
        # Verify a specific account
        acct = accounting_db.get_account("1002")
        assert acct["name"] == "银行存款"

    def test_init_periods(self, accounting_db):
        count = init_periods(accounting_db, 2026)
        assert count == 12
        periods = accounting_db.list_periods()
        assert len(periods) == 12
        assert periods[0]["start_date"] == "2026-01-01"
        assert periods[11]["end_date"] == "2026-12-31"
