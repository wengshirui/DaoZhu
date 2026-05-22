"""Tests for quality_engine — auto quality check on vouchers.

TDD: tests written first based on REQ-021 acceptance criteria.
"""

import json
import time
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.fixture
def mock_db(tmp_path):
    """Create a real AccountingDB instance with test data."""
    from accobot.db.accounting import AccountingDB
    db = AccountingDB("test_company", db_path=tmp_path / "test.db")

    # Add basic accounts
    db.add_account("1001", "库存现金", "asset", "debit", is_leaf=True)
    db.add_account("1002", "银行存款", "asset", "debit", is_leaf=True)
    db.add_account("6602", "管理费用", "expense", "debit", is_leaf=True)
    db.add_account("2202", "应付账款", "liability", "credit", is_leaf=True)
    db.add_account("6001", "主营业务收入", "income", "credit", is_leaf=True)

    return db


@pytest.fixture
def balanced_voucher(mock_db):
    """Create a balanced voucher (debit == credit)."""
    mock_db.create_voucher("V001", "2026-05-22", summary="付办公用品")
    mock_db.add_entry("V001", "6602", debit=1000, credit=0, summary="办公用品")
    mock_db.add_entry("V001", "1002", debit=0, credit=1000, summary="银行付款")
    return "V001"


@pytest.fixture
def unbalanced_voucher(mock_db):
    """Create an unbalanced voucher."""
    mock_db.create_voucher("V002", "2026-05-22", summary="测试不平衡")
    mock_db.add_entry("V002", "6602", debit=1000, credit=0)
    mock_db.add_entry("V002", "1002", debit=0, credit=500)
    return "V002"


@pytest.fixture
def empty_summary_voucher(mock_db):
    """Create a voucher with empty summary."""
    mock_db.create_voucher("V003", "2026-05-22", summary="")
    mock_db.add_entry("V003", "6602", debit=100, credit=0)
    mock_db.add_entry("V003", "1002", debit=0, credit=100)
    return "V003"


@pytest.fixture
def large_cash_voucher(mock_db):
    """Create a voucher with large cash transaction (>50000)."""
    mock_db.create_voucher("V004", "2026-05-22", summary="大额现金支出")
    mock_db.add_entry("V004", "6602", debit=60000, credit=0)
    mock_db.add_entry("V004", "1001", debit=0, credit=60000)
    return "V004"


@pytest.fixture
def no_entries_voucher(mock_db):
    """Create a voucher with no entries."""
    mock_db.create_voucher("V005", "2026-05-22", summary="空凭证")
    return "V005"


# =========================================================================
# Story 1: Quality Engine + Persistence
# =========================================================================

class TestQualityEngine:
    """Test run_quality_check() function."""

    def test_balanced_voucher_passes(self, mock_db, balanced_voucher):
        """AC-1: Balanced voucher with summary should pass all checks."""
        from accobot.tools.quality_engine import run_quality_check

        result = run_quality_check(balanced_voucher, mock_db)
        assert result.passed is True
        # May have warnings (e.g. balance direction on empty DB) but no critical
        assert not any(i.level == "critical" for i in result.issues)

    def test_unbalanced_voucher_fails(self, mock_db, unbalanced_voucher):
        """AC-3: Unbalanced voucher should produce critical issue."""
        from accobot.tools.quality_engine import run_quality_check

        result = run_quality_check(unbalanced_voucher, mock_db)
        assert result.passed is False
        critical = [i for i in result.issues if i.level == "critical"]
        assert len(critical) >= 1
        assert "平衡" in critical[0].message or "不相等" in critical[0].message

    def test_empty_summary_warning(self, mock_db, empty_summary_voucher):
        """AC-3: Empty summary should produce warning (not critical)."""
        from accobot.tools.quality_engine import run_quality_check

        result = run_quality_check(empty_summary_voucher, mock_db)
        # Empty summary is warning, not critical — voucher still passes
        assert result.passed is True
        warnings = [i for i in result.issues if i.level == "warning"]
        assert len(warnings) >= 1
        assert "摘要" in warnings[0].message

    def test_large_cash_warning(self, mock_db, large_cash_voucher):
        """AC-3: Large cash (>50000) should produce warning."""
        from accobot.tools.quality_engine import run_quality_check

        result = run_quality_check(large_cash_voucher, mock_db)
        assert result.passed is True  # warning doesn't fail
        warnings = [i for i in result.issues if i.level == "warning"]
        assert any("现金" in w.message or "5" in w.message for w in warnings)

    def test_no_entries_fails(self, mock_db, no_entries_voucher):
        """AC-3: Voucher with no entries should produce critical issue."""
        from accobot.tools.quality_engine import run_quality_check

        result = run_quality_check(no_entries_voucher, mock_db)
        assert result.passed is False
        critical = [i for i in result.issues if i.level == "critical"]
        assert len(critical) >= 1
        assert "分录" in critical[0].message

    def test_nonexistent_voucher(self, mock_db):
        """Edge case: non-existent voucher should return failed result."""
        from accobot.tools.quality_engine import run_quality_check

        result = run_quality_check("NONEXIST", mock_db)
        assert result.passed is False
        assert len(result.issues) >= 1

    def test_result_has_checked_at(self, mock_db, balanced_voucher):
        """AC-1: Result should include timestamp."""
        from accobot.tools.quality_engine import run_quality_check

        before = time.time()
        result = run_quality_check(balanced_voucher, mock_db)
        after = time.time()
        assert before <= result.checked_at <= after


class TestQualityPersistence:
    """Test quality check result persistence."""

    def test_save_and_retrieve(self, mock_db, balanced_voucher):
        """AC-2: Quality result can be saved and retrieved."""
        from accobot.tools.quality_engine import run_quality_check, save_quality_result, get_quality_result

        result = run_quality_check(balanced_voucher, mock_db)
        record_id = save_quality_result(balanced_voucher, result, mock_db)
        assert record_id > 0

        saved = get_quality_result(balanced_voucher, mock_db)
        assert saved is not None
        assert saved["passed"] == 1
        assert saved["voucher_id"] == balanced_voucher

    def test_save_failed_result(self, mock_db, unbalanced_voucher):
        """AC-2: Failed quality result is persisted with issues."""
        from accobot.tools.quality_engine import run_quality_check, save_quality_result, get_quality_result

        result = run_quality_check(unbalanced_voucher, mock_db)
        save_quality_result(unbalanced_voucher, result, mock_db)

        saved = get_quality_result(unbalanced_voucher, mock_db)
        assert saved["passed"] == 0
        issues = json.loads(saved["issues"])
        assert len(issues) >= 1


# =========================================================================
# Story 2: Auto-trigger on post
# =========================================================================

class TestAutoTriggerOnPost:
    """Test that quality check is auto-triggered before posting."""

    def test_create_voucher_with_entries_triggers_qc(self, mock_db, tmp_path):
        """AC-1: create_voucher_with_entries auto-triggers quality check."""
        # We test this by checking that a balanced voucher gets posted
        # and an unbalanced one doesn't
        from accobot.tools.quality_engine import get_quality_result

        # Create a balanced voucher via the tool
        from accobot.tools.voucher_tool import create_voucher_with_entries

        with patch("accobot.tools.voucher_tool._get_db", return_value=mock_db):
            result_json = create_voucher_with_entries({
                "date": "2026-05-22",
                "summary": "测试自动质检",
                "entries": [
                    {"account_code": "6602", "debit": 500, "credit": 0},
                    {"account_code": "1002", "debit": 0, "credit": 500},
                ],
            })

        result = json.loads(result_json)
        assert result.get("success") is True
        # Voucher should be posted (quality check passed)
        assert "过账" in result.get("message", "")

    def test_post_voucher_blocks_on_critical(self, mock_db, unbalanced_voucher):
        """AC-2/AC-3: post_voucher blocks when critical issues found."""
        from accobot.tools.voucher_tool import post_voucher

        with patch("accobot.tools.voucher_tool._get_db", return_value=mock_db):
            result_json = post_voucher({"voucher_id": unbalanced_voucher})

        result = json.loads(result_json)
        assert "error" in result
        # Voucher should remain draft
        voucher = mock_db.get_voucher_with_entries(unbalanced_voucher)
        assert voucher["status"] == "draft"

    def test_warning_does_not_block_post(self, mock_db, large_cash_voucher):
        """AC-4: Warning-level issues don't block posting."""
        from accobot.tools.voucher_tool import post_voucher

        with patch("accobot.tools.voucher_tool._get_db", return_value=mock_db):
            result_json = post_voucher({"voucher_id": large_cash_voucher})

        result = json.loads(result_json)
        assert result.get("success") is True or "过账" in result.get("message", "")
        # Voucher should be posted despite warning
        voucher = mock_db.get_voucher_with_entries(large_cash_voucher)
        assert voucher["status"] == "posted"
