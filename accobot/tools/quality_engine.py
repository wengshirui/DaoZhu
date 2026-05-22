"""Quality check engine — reusable quality validation for vouchers.

Extracted from quality_check_tool.py to enable auto-triggering.
This module has NO tool registration — it's a pure logic module
called by voucher_tool.py (auto) and quality_check_tool.py (manual).

REQ-021: 凭证事后质检自动触发
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Threshold for large cash transactions (CNY)
LARGE_CASH_THRESHOLD = 50000


@dataclass
class QualityIssue:
    """A single quality check issue."""
    level: str       # "critical" | "warning" | "info"
    rule: str        # Rule identifier, e.g. "balance_check"
    message: str     # User-readable message (plain language)


@dataclass
class QualityResult:
    """Result of a quality check on a single voucher."""
    passed: bool
    issues: List[QualityIssue] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)

    @property
    def has_critical(self) -> bool:
        return any(i.level == "critical" for i in self.issues)

    @property
    def warnings(self) -> List[QualityIssue]:
        return [i for i in self.issues if i.level == "warning"]


def run_quality_check(voucher_id: str, db) -> QualityResult:
    """Run quality checks on a single voucher.

    Args:
        voucher_id: The voucher to check.
        db: AccountingDB instance.

    Returns:
        QualityResult with pass/fail status and issue list.
    """
    issues: List[QualityIssue] = []

    # Load voucher
    voucher = db.get_voucher_with_entries(voucher_id)
    if not voucher:
        return QualityResult(
            passed=False,
            issues=[QualityIssue("critical", "not_found", f"凭证 {voucher_id} 不存在")],
        )

    entries = voucher.get("entries", [])

    # Rule 1: Empty summary (check before entries since it applies regardless)
    if not voucher.get("summary", "").strip():
        issues.append(QualityIssue(
            "warning", "empty_summary",
            '凭证摘要为空，建议填写用途说明（如"付房租"、"收货款"）',
        ))

    # Rule 2: Must have entries
    if not entries:
        issues.append(QualityIssue(
            "critical", "no_entries",
            "这张凭证没有分录，无法记账",
        ))
        # No point checking further
        return QualityResult(passed=False, issues=issues)

    # Rule 3: Debit/Credit balance
    total_debit = sum(e["debit"] for e in entries)
    total_credit = sum(e["credit"] for e in entries)
    if abs(total_debit - total_credit) > 0.01:
        issues.append(QualityIssue(
            "critical", "balance_check",
            f"这笔分录借方合计（{total_debit:.2f}）和贷方合计（{total_credit:.2f}）不相等，差额 {abs(total_debit - total_credit):.2f}",
        ))

    # Rule 4: Large cash transactions
    for e in entries:
        if e["account_code"] == "1001":
            amount = max(e["debit"], e["credit"])
            if amount > LARGE_CASH_THRESHOLD:
                issues.append(QualityIssue(
                    "warning", "large_cash",
                    f"大额现金交易 {amount:,.2f} 元（超过 {LARGE_CASH_THRESHOLD:,.0f} 元），请确认是否合规",
                ))

    # Rule 5: Account balance direction anomaly (check affected accounts)
    _check_balance_direction(entries, db, issues)

    # Determine pass/fail: critical issues → fail
    passed = not any(i.level == "critical" for i in issues)

    return QualityResult(passed=passed, issues=issues)


def _check_balance_direction(entries: List[Dict], db, issues: List[QualityIssue]) -> None:
    """Check if any account would have an abnormal balance direction after posting."""
    # Get unique account codes from entries
    account_codes = set(e["account_code"] for e in entries)

    for code in account_codes:
        account = db.get_account(code)
        if not account:
            continue

        # Get current balance
        bal = db.get_account_balance(code)
        current_balance = bal["balance"]

        # Calculate what the new balance would be after this voucher
        entry_debit = sum(e["debit"] for e in entries if e["account_code"] == code)
        entry_credit = sum(e["credit"] for e in entries if e["account_code"] == code)

        if account["balance_direction"] == "debit":
            new_balance = current_balance + entry_debit - entry_credit
        else:
            new_balance = current_balance + entry_credit - entry_debit

        # Check for anomaly
        category = account["category"]
        if category == "asset" and new_balance < -0.01:
            issues.append(QualityIssue(
                "warning", "balance_direction_anomaly",
                f"资产科目「{account['name']}」过账后将出现贷方余额（{new_balance:.2f}），请检查是否正确",
            ))
        elif category == "liability" and new_balance < -0.01:
            issues.append(QualityIssue(
                "warning", "balance_direction_anomaly",
                f"负债科目「{account['name']}」过账后将出现借方余额，请检查是否正确",
            ))


# =========================================================================
# Persistence
# =========================================================================

# Schema addition for quality_checks table
QUALITY_CHECK_SCHEMA = """
CREATE TABLE IF NOT EXISTS quality_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id TEXT NOT NULL,
    checked_at REAL NOT NULL,
    passed INTEGER NOT NULL DEFAULT 0,
    issues TEXT NOT NULL DEFAULT '[]',
    extra TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_qc_voucher ON quality_checks(voucher_id);
"""


def _ensure_qc_table(db) -> None:
    """Ensure the quality_checks table exists."""
    with db._lock:
        db._conn.executescript(QUALITY_CHECK_SCHEMA)


def save_quality_result(voucher_id: str, result: QualityResult, db) -> int:
    """Persist a quality check result to the database.

    Returns the record ID.
    """
    _ensure_qc_table(db)

    issues_json = json.dumps(
        [{"level": i.level, "rule": i.rule, "message": i.message} for i in result.issues],
        ensure_ascii=False,
    )

    with db._lock:
        cur = db._conn.execute(
            """INSERT INTO quality_checks (voucher_id, checked_at, passed, issues)
               VALUES (?, ?, ?, ?)""",
            (voucher_id, result.checked_at, int(result.passed), issues_json),
        )
        return cur.lastrowid


def get_quality_result(voucher_id: str, db) -> Optional[Dict[str, Any]]:
    """Get the latest quality check result for a voucher.

    Returns dict with keys: id, voucher_id, checked_at, passed, issues (JSON string).
    """
    _ensure_qc_table(db)

    with db._lock:
        cur = db._conn.execute(
            "SELECT * FROM quality_checks WHERE voucher_id = ? ORDER BY checked_at DESC LIMIT 1",
            (voucher_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
