"""Tests for voucher and ledger tools with real database."""

import os
import json
from unittest.mock import patch
import pytest
from accobot.db.manager import DBManager


@pytest.fixture(autouse=True)
def isolated_env(tmp_path):
    with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path)}):
        DBManager.reset()
        mgr = DBManager.get_instance()
        mgr.create_company("测试公司")
        yield mgr
        DBManager.reset()


class TestCreateVoucherWithEntries:
    def test_basic_voucher(self, isolated_env):
        from accobot.tools.voucher_tool import create_voucher_with_entries
        result = json.loads(create_voucher_with_entries({
            "summary": "付房租",
            "entries": [
                {"account_code": "560203", "debit": 5000},
                {"account_code": "1002", "credit": 5000},
            ],
        }))
        assert result["success"] is True
        assert "voucher_id" in result
        assert "付房租" in result["message"]

    def test_unbalanced_entries_rejected(self, isolated_env):
        from accobot.tools.voucher_tool import create_voucher_with_entries
        result = json.loads(create_voucher_with_entries({
            "summary": "错误凭证",
            "entries": [
                {"account_code": "560203", "debit": 5000},
                {"account_code": "1002", "credit": 3000},
            ],
        }))
        assert "error" in result
        assert "不平衡" in result["error"]

    def test_missing_entries_rejected(self, isolated_env):
        from accobot.tools.voucher_tool import create_voucher_with_entries
        result = json.loads(create_voucher_with_entries({"summary": "test", "entries": []}))
        assert "error" in result

    def test_invalid_account_rejected(self, isolated_env):
        from accobot.tools.voucher_tool import create_voucher_with_entries
        result = json.loads(create_voucher_with_entries({
            "summary": "test",
            "entries": [
                {"account_code": "999999", "debit": 100},
                {"account_code": "1002", "credit": 100},
            ],
        }))
        assert "error" in result
        assert "不存在" in result["error"]


class TestQueryVouchers:
    def test_empty_list(self, isolated_env):
        from accobot.tools.voucher_tool import query_vouchers
        result = json.loads(query_vouchers({}))
        assert result["success"] is True

    def test_after_create(self, isolated_env):
        from accobot.tools.voucher_tool import create_voucher_with_entries, query_vouchers
        create_voucher_with_entries({
            "summary": "测试",
            "entries": [{"account_code": "1001", "debit": 100}, {"account_code": "1002", "credit": 100}],
        })
        result = json.loads(query_vouchers({}))
        assert result["count"] == 1


class TestPostVoucher:
    def test_post_success(self, isolated_env):
        from accobot.tools.voucher_tool import create_voucher_with_entries, post_voucher
        r = json.loads(create_voucher_with_entries({
            "summary": "测试过账",
            "entries": [{"account_code": "1001", "debit": 1000}, {"account_code": "1002", "credit": 1000}],
        }))
        vid = r["voucher_id"]
        post_result = json.loads(post_voucher({"voucher_id": vid}))
        assert post_result["success"] is True

    def test_post_already_posted(self, isolated_env):
        from accobot.tools.voucher_tool import create_voucher_with_entries, post_voucher
        r = json.loads(create_voucher_with_entries({
            "summary": "test",
            "entries": [{"account_code": "1001", "debit": 100}, {"account_code": "1002", "credit": 100}],
        }))
        vid = r["voucher_id"]
        post_voucher({"voucher_id": vid})
        result = json.loads(post_voucher({"voucher_id": vid}))
        assert "error" in result


class TestLedgerTools:
    def _create_and_post(self):
        from accobot.tools.voucher_tool import create_voucher_with_entries, post_voucher
        r = json.loads(create_voucher_with_entries({
            "summary": "收款",
            "entries": [{"account_code": "1002", "debit": 10000}, {"account_code": "5001", "credit": 10000}],
        }))
        post_voucher({"voucher_id": r["voucher_id"]})

    def test_query_balance(self, isolated_env):
        self._create_and_post()
        from accobot.tools.ledger_tool import query_balance
        result = json.loads(query_balance({"account_name": "银行存款"}))
        assert result["success"] is True
        assert result["balance"] == 10000

    def test_query_detail(self, isolated_env):
        self._create_and_post()
        from accobot.tools.ledger_tool import query_detail
        result = json.loads(query_detail({"account_name": "银行存款"}))
        assert result["success"] is True
        assert result["count"] == 1

    def test_trial_balance(self, isolated_env):
        self._create_and_post()
        from accobot.tools.ledger_tool import trial_balance
        result = json.loads(trial_balance({}))
        assert result["success"] is True
        assert result["count"] >= 2  # At least bank + revenue

    def test_no_data(self, isolated_env):
        from accobot.tools.ledger_tool import trial_balance
        result = json.loads(trial_balance({}))
        assert result["success"] is True
        assert "暂无" in result["message"]
