"""Tests for tax, reconciliation, and quality check tools."""

import os
import json
from unittest.mock import patch
import pytest
from accobot.db.manager import DBManager


@pytest.fixture(autouse=True)
def env_with_data(tmp_path):
    with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path)}):
        DBManager.reset()
        mgr = DBManager.get_instance()
        mgr.create_company("税务测试公司", taxpayer_type="small_scale")
        db = mgr.accounting
        # Revenue
        db.create_voucher("V001", "2026-05-01", summary="收货款")
        db.add_entry("V001", "1002", debit=100000)
        db.add_entry("V001", "5001", credit=100000)
        db.update_voucher_status("V001", "posted")
        # Expense
        db.create_voucher("V002", "2026-05-05", summary="付房租")
        db.add_entry("V002", "560203", debit=5000)
        db.add_entry("V002", "1002", credit=5000)
        db.update_voucher_status("V002", "posted")
        yield mgr
        DBManager.reset()


class TestVAT:
    def test_small_scale_vat(self, env_with_data):
        from accobot.tools.tax_tool import calculate_vat
        result = json.loads(calculate_vat({}))
        assert result["success"] is True
        assert result["revenue"] == 100000
        assert result["taxpayer_type"] == "small_scale"
        # Quarterly < 300000, should be exempt
        assert result["exempt"] is True
        assert result["vat"] == 0

    def test_surcharges_zero_when_exempt(self, env_with_data):
        from accobot.tools.tax_tool import calculate_surcharges
        result = json.loads(calculate_surcharges({"vat_amount": 0}))
        assert result["success"] is True
        assert result["total"] == 0

    def test_surcharges_with_vat(self, env_with_data):
        from accobot.tools.tax_tool import calculate_surcharges
        result = json.loads(calculate_surcharges({"vat_amount": 1000}))
        assert result["success"] is True
        # Small scale: (7%+3%+2%) * 50% = 6% of VAT
        assert result["total"] == 60.0  # 1000 * 0.12 * 0.5

    def test_tax_calendar(self, env_with_data):
        from accobot.tools.tax_tool import tax_calendar
        result = json.loads(tax_calendar({}))
        assert result["success"] is True


class TestReconciliation:
    def test_import_and_match(self, env_with_data):
        from accobot.tools.reconciliation_tool import import_bank_transactions, auto_reconcile
        # Import a transaction matching V001
        import_result = json.loads(import_bank_transactions({
            "transactions": [
                {"date": "2026-05-01", "amount": 100000, "direction": "debit", "counterparty": "客户A", "summary": "货款"},
                {"date": "2026-05-05", "amount": 5000, "direction": "credit", "counterparty": "物业", "summary": "房租"},
            ]
        }))
        assert import_result["success"] is True
        assert import_result["imported"] == 2

        # Auto reconcile
        recon_result = json.loads(auto_reconcile({}))
        assert recon_result["success"] is True
        assert recon_result["matched"] == 2
        assert recon_result["unmatched"] == 0

    def test_unmatched_transactions(self, env_with_data):
        from accobot.tools.reconciliation_tool import import_bank_transactions, auto_reconcile
        import_bank_transactions({
            "transactions": [
                {"date": "2026-05-20", "amount": 9999, "direction": "debit", "counterparty": "未知"},
            ]
        })
        result = json.loads(auto_reconcile({}))
        assert result["unmatched"] == 1


class TestQualityCheck:
    def test_passes_clean_data(self, env_with_data):
        from accobot.tools.quality_check_tool import check_vouchers
        result = json.loads(check_vouchers({}))
        assert result["success"] is True
        # Should have no critical issues for our clean test data
        assert result.get("critical", 0) == 0

    def test_detects_empty_voucher(self, env_with_data):
        from accobot.tools.quality_check_tool import check_vouchers
        db = env_with_data.accounting
        db.create_voucher("VBAD", "2026-05-15", summary="")
        result = json.loads(check_vouchers({}))
        # Should detect empty summary and no entries
        issues = result.get("issues", [])
        assert any("摘要为空" in i["message"] for i in issues)
