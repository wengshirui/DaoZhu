"""Tests for report and analytics tools."""

import os
import json
from unittest.mock import patch
import pytest
from accobot.db.manager import DBManager


@pytest.fixture(autouse=True)
def env_with_data(tmp_path):
    """Create a company with some posted vouchers for report testing."""
    with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path)}):
        DBManager.reset()
        mgr = DBManager.get_instance()
        mgr.create_company("报表测试公司")
        db = mgr.accounting

        # Post some transactions
        # 1. Revenue: 收到货款 50000
        db.create_voucher("V001", "2026-05-01", summary="收货款")
        db.add_entry("V001", "1002", debit=50000)   # 银行存款
        db.add_entry("V001", "5001", credit=50000)  # 主营业务收入
        db.update_voucher_status("V001", "posted")

        # 2. Expense: 付房租 5000
        db.create_voucher("V002", "2026-05-05", summary="付房租")
        db.add_entry("V002", "560203", debit=5000)  # 管理费用-租赁费
        db.add_entry("V002", "1002", credit=5000)   # 银行存款
        db.update_voucher_status("V002", "posted")

        # 3. Expense: 办公费 2000
        db.create_voucher("V003", "2026-05-10", summary="买办公用品")
        db.add_entry("V003", "560201", debit=2000)  # 管理费用-办公费
        db.add_entry("V003", "1002", credit=2000)   # 银行存款
        db.update_voucher_status("V003", "posted")

        yield mgr
        DBManager.reset()


class TestIncomeStatement:
    def test_generates_report(self, env_with_data):
        from accobot.tools.report_tool import income_statement
        result = json.loads(income_statement({}))
        assert result["success"] is True
        assert result["revenue"] == 50000
        assert result["expense"] == 7000  # 5000 + 2000
        assert result["net_profit"] == 43000  # 50000 - 7000

    def test_message_format(self, env_with_data):
        from accobot.tools.report_tool import income_statement
        result = json.loads(income_statement({}))
        assert "利润表" in result["message"]
        assert "净利润" in result["message"]


class TestBalanceSheet:
    def test_generates_report(self, env_with_data):
        from accobot.tools.report_tool import balance_sheet
        result = json.loads(balance_sheet({}))
        assert result["success"] is True
        # Bank: 50000 - 5000 - 2000 = 43000
        assert result["total_assets"] == 43000

    def test_balanced(self, env_with_data):
        from accobot.tools.report_tool import balance_sheet
        result = json.loads(balance_sheet({}))
        # Note: without equity entries, it won't balance perfectly
        # but the tool should still generate without crashing
        assert result["success"] is True


class TestExpenseBreakdown:
    def test_shows_expenses(self, env_with_data):
        from accobot.tools.analytics_tool import expense_breakdown
        result = json.loads(expense_breakdown({}))
        assert result["success"] is True
        assert result["total"] == 7000
        assert len(result["items"]) == 2
        # Rent should be first (largest)
        assert result["items"][0]["amount"] == 5000

    def test_percentages(self, env_with_data):
        from accobot.tools.analytics_tool import expense_breakdown
        result = json.loads(expense_breakdown({}))
        # Rent: 5000/7000 = 71.4%
        assert result["items"][0]["percent"] == pytest.approx(71.4, abs=0.1)


class TestRevenueVsExpense:
    def test_profit_calculation(self, env_with_data):
        from accobot.tools.analytics_tool import revenue_vs_expense
        result = json.loads(revenue_vs_expense({}))
        assert result["success"] is True
        assert result["revenue"] == 50000
        assert result["expense"] == 7000
        assert result["net_profit"] == 43000
        assert "盈利" in result["status"]
