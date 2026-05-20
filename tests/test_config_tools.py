"""Tests for config tools (accounts, aux items, periods)."""

import os
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from accobot.db.manager import DBManager
from accobot.db.templates import init_accounts, init_periods


@pytest.fixture(autouse=True)
def isolated_env(tmp_path):
    with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path)}):
        DBManager.reset()
        mgr = DBManager.get_instance()
        mgr.create_company("测试公司")
        yield mgr
        DBManager.reset()


class TestListAccounts:
    def test_returns_accounts(self, isolated_env):
        from accobot.tools.config_tool import list_accounts
        result = json.loads(list_accounts({}))
        assert result["success"] is True
        assert result["count"] > 50

    def test_filter_by_category(self, isolated_env):
        from accobot.tools.config_tool import list_accounts
        result = json.loads(list_accounts({"category": "asset"}))
        assert result["success"] is True
        for a in result["accounts"]:
            assert a["category"] == "asset"

    def test_search_by_keyword(self, isolated_env):
        from accobot.tools.config_tool import list_accounts
        result = json.loads(list_accounts({"keyword": "银行"}))
        assert result["success"] is True
        assert any("银行" in a["name"] for a in result["accounts"])

    def test_no_company_returns_error(self, tmp_path):
        from accobot.tools.config_tool import list_accounts
        with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path / "empty")}):
            DBManager.reset()
            _mgr = DBManager.get_instance()
            # No company created, accounting is None
            result = json.loads(list_accounts({}))
            assert "error" in result
            assert "账套" in result["error"]
            DBManager.reset()


class TestAddAccount:
    def test_add_new_account(self, isolated_env):
        from accobot.tools.config_tool import add_account
        result = json.loads(add_account({
            "code": "560299", "name": "测试费用", "category": "expense",
        }))
        assert result["success"] is True
        assert "560299" in result["message"]

    def test_duplicate_code_error(self, isolated_env):
        from accobot.tools.config_tool import add_account
        result = json.loads(add_account({
            "code": "1001", "name": "重复科目", "category": "asset",
        }))
        assert "error" in result
        assert "已存在" in result["error"]

    def test_missing_fields_error(self, isolated_env):
        from accobot.tools.config_tool import add_account
        result = json.loads(add_account({"code": "9999"}))
        assert "error" in result


class TestAuxItems:
    def test_add_and_list(self, isolated_env):
        from accobot.tools.config_tool import add_aux_item, list_aux_items
        add_result = json.loads(add_aux_item({"type": "department", "name": "财务部"}))
        assert add_result["success"] is True

        list_result = json.loads(list_aux_items({"type": "department"}))
        assert list_result["success"] is True
        assert list_result["count"] == 1
        assert list_result["items"][0]["name"] == "财务部"

    def test_invalid_type_error(self, isolated_env):
        from accobot.tools.config_tool import add_aux_item
        result = json.loads(add_aux_item({"type": "invalid", "name": "test"}))
        assert "error" in result


class TestPeriods:
    def test_list_periods(self, isolated_env):
        from accobot.tools.config_tool import list_periods
        result = json.loads(list_periods({}))
        assert result["success"] is True
        assert result["count"] == 12

    def test_close_and_open_period(self, isolated_env):
        from accobot.tools.config_tool import close_period, open_period
        close_result = json.loads(close_period({"period_id": "2026-01"}))
        assert close_result["success"] is True

        open_result = json.loads(open_period({"period_id": "2026-01"}))
        assert open_result["success"] is True

    def test_close_nonexistent_period(self, isolated_env):
        from accobot.tools.config_tool import close_period
        result = json.loads(close_period({"period_id": "9999-99"}))
        assert "error" in result

    def test_generate_new_year(self, isolated_env):
        from accobot.tools.config_tool import generate_periods
        result = json.loads(generate_periods({"year": 2027}))
        assert result["success"] is True
        assert result["count"] == 12
