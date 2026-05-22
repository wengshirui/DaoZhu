"""Tests for accounting standards — REQ-023.

Verifies standard document generation, template loading, and rules content.
"""

import json
import pytest
from pathlib import Path


class TestStandardDocGeneration:
    """Test generate_standard_docs() creates correct files."""

    def test_generates_small_enterprise_docs(self, tmp_path):
        """AC-1: Creates accounting_rules.md and chart_of_accounts.json."""
        from accobot.db.standards import generate_standard_docs

        result = generate_standard_docs(tmp_path, "small_enterprise")
        assert result is True

        rules_path = tmp_path / "standard" / "accounting_rules.md"
        chart_path = tmp_path / "standard" / "chart_of_accounts.json"

        assert rules_path.exists()
        assert chart_path.exists()

    def test_generates_enterprise_docs(self, tmp_path):
        """AC-1: Creates docs for enterprise standard too."""
        from accobot.db.standards import generate_standard_docs

        result = generate_standard_docs(tmp_path, "enterprise")
        assert result is True

        rules_path = tmp_path / "standard" / "accounting_rules.md"
        assert rules_path.exists()
        content = rules_path.read_text(encoding="utf-8")
        assert "企业会计准则" in content

    def test_rules_content_small_enterprise(self, tmp_path):
        """AC-2: Small enterprise rules mention key constraints."""
        from accobot.db.standards import generate_standard_docs

        generate_standard_docs(tmp_path, "small_enterprise")
        content = (tmp_path / "standard" / "accounting_rules.md").read_text(encoding="utf-8")

        assert "小企业会计准则" in content
        assert "递延所得税" in content
        assert "坏账准备" in content
        assert "Agent 做账约束" in content

    def test_rules_content_enterprise(self, tmp_path):
        """AC-2: Enterprise rules mention different constraints."""
        from accobot.db.standards import generate_standard_docs

        generate_standard_docs(tmp_path, "enterprise")
        content = (tmp_path / "standard" / "accounting_rules.md").read_text(encoding="utf-8")

        assert "企业会计准则" in content
        assert "预期信用损失" in content
        assert "现金流量表" in content

    def test_chart_json_valid(self, tmp_path):
        """AC-1: chart_of_accounts.json is valid JSON with accounts."""
        from accobot.db.standards import generate_standard_docs

        generate_standard_docs(tmp_path, "small_enterprise")
        chart_path = tmp_path / "standard" / "chart_of_accounts.json"
        data = json.loads(chart_path.read_text(encoding="utf-8"))

        assert data["standard"] == "small_enterprise"
        assert data["account_count"] > 50
        assert len(data["accounts"]) == data["account_count"]
        # Verify account structure
        first = data["accounts"][0]
        assert "code" in first
        assert "name" in first
        assert "category" in first


class TestEnterpriseTemplate:
    """Test enterprise accounting standard template."""

    def test_enterprise_template_loads(self):
        """AC-1: Enterprise template loads successfully."""
        from accobot.db.templates import load_template

        accounts = load_template("enterprise")
        assert len(accounts) > 50

    def test_enterprise_has_deferred_tax(self):
        """AC-1: Enterprise template includes deferred tax accounts."""
        from accobot.db.templates import load_template

        accounts = load_template("enterprise")
        codes = [a[0] for a in accounts]
        names = [a[1] for a in accounts]

        assert "1811" in codes  # 递延所得税资产
        assert "2601" in codes  # 递延所得税负债
        assert "递延所得税资产" in names
        assert "递延所得税负债" in names

    def test_enterprise_has_impairment(self):
        """AC-1: Enterprise template includes asset impairment accounts."""
        from accobot.db.templates import load_template

        accounts = load_template("enterprise")
        names = [a[1] for a in accounts]

        assert "坏账准备" in names
        assert "资产减值损失" in names

    def test_small_enterprise_no_deferred_tax(self):
        """AC-3: Small enterprise does NOT have deferred tax."""
        from accobot.db.templates import load_template

        accounts = load_template("small_enterprise")
        names = [a[1] for a in accounts]

        assert "递延所得税资产" not in names
        assert "递延所得税负债" not in names

    def test_common_codes_consistent(self):
        """AC-3: Common accounts have same codes across standards."""
        from accobot.db.templates import load_template

        small = {a[0]: a[1] for a in load_template("small_enterprise")}
        enterprise = {a[0]: a[1] for a in load_template("enterprise")}

        # Core accounts should match
        common_codes = ["1001", "1002", "1122", "2202", "5001", "5602"]
        for code in common_codes:
            assert code in small, f"{code} missing from small_enterprise"
            assert code in enterprise, f"{code} missing from enterprise"
            assert small[code] == enterprise[code], f"Name mismatch for {code}"


class TestStandardRulesLoading:
    """Test loading standard rules for system prompt."""

    def test_load_summary_returns_content(self, tmp_path):
        """AC-4: load_standard_rules_summary returns content when docs exist."""
        from accobot.db.standards import generate_standard_docs, load_standard_rules_summary

        generate_standard_docs(tmp_path, "small_enterprise")
        summary = load_standard_rules_summary(tmp_path)

        assert len(summary) > 0
        assert "会计准则" in summary

    def test_load_summary_empty_when_no_docs(self, tmp_path):
        """Edge case: returns empty string when no standard docs."""
        from accobot.db.standards import load_standard_rules_summary

        summary = load_standard_rules_summary(tmp_path)
        assert summary == ""
