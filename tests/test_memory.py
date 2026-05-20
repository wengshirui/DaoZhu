"""Tests for memory and learning tools."""

import os
import json
from unittest.mock import patch
import pytest
from accobot.db.manager import DBManager


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    with patch.dict(os.environ, {"ACCOBOT_HOME": str(tmp_path)}):
        DBManager.reset()
        mgr = DBManager.get_instance()
        mgr.create_company("记忆测试")
        yield mgr
        DBManager.reset()


class TestMemory:
    def test_remember_and_recall(self, isolated):
        from accobot.tools.memory_tool import remember, recall
        r = json.loads(remember({"key": "快递费科目", "value": "管理费用-邮寄费 560210", "category": "pattern"}))
        assert r["success"] is True

        r2 = json.loads(recall({"keyword": "快递"}))
        assert r2["success"] is True
        assert len(r2["memories"]) == 1
        assert "邮寄费" in r2["memories"][0]["value"]

    def test_remember_updates_existing(self, isolated):
        from accobot.tools.memory_tool import remember, recall
        remember({"key": "房租科目", "value": "办公费"})
        remember({"key": "房租科目", "value": "租赁费"})  # Update
        r = json.loads(recall({"keyword": "房租"}))
        assert r["memories"][0]["value"] == "租赁费"

    def test_forget(self, isolated):
        from accobot.tools.memory_tool import remember, forget, recall
        remember({"key": "测试记忆", "value": "test"})
        json.loads(forget({"key": "测试"}))
        r = json.loads(recall({"keyword": "测试"}))
        assert len(r["memories"]) == 0


class TestLearning:
    def test_record_and_progress(self, isolated):
        from accobot.tools.memory_tool import record_learning, learning_progress
        record_learning({"title": "进项税额", "category": "tax", "content": "购买商品时支付的增值税"})
        record_learning({"title": "借贷记账法", "category": "accounting"})

        r = json.loads(learning_progress({}))
        assert r["success"] is True
        assert len(r["points"]) == 2

    def test_repeated_review_increments_count(self, isolated):
        from accobot.tools.memory_tool import record_learning, learning_progress
        record_learning({"title": "权责发生制"})
        record_learning({"title": "权责发生制"})  # Review again
        r = json.loads(learning_progress({}))
        point = next(p for p in r["points"] if p["title"] == "权责发生制")
        assert point["review_count"] == 2
