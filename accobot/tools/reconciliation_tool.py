"""Bank reconciliation tools — import bank statements, auto-match.

Toolset: "reconciliation"
Import bank transaction data and match against posted voucher entries.
"""

import json
import uuid
from datetime import date, timedelta
from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


def _ensure_bank_table(db):
    """Ensure bank_transactions table exists."""
    with db._lock:
        db._conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_transactions (
                id TEXT PRIMARY KEY,
                trans_date TEXT NOT NULL,
                amount REAL NOT NULL,
                direction TEXT NOT NULL,
                counterparty TEXT,
                summary TEXT,
                bank_ref TEXT,
                matched_voucher_id TEXT,
                matched_at REAL,
                status TEXT DEFAULT 'unmatched'
            )
        """)
        db._conn.execute("CREATE INDEX IF NOT EXISTS idx_bank_date ON bank_transactions(trans_date)")


def import_bank_transactions(args: dict, **kwargs) -> str:
    """Import bank transactions from structured data."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    _ensure_bank_table(db)
    transactions = args.get("transactions", [])

    if not transactions:
        return tool_error("没有提供银行流水数据")

    imported = 0
    with db._lock:
        for t in transactions:
            trans_id = t.get("id", uuid.uuid4().hex[:10])
            trans_date = t.get("date", date.today().isoformat())
            amount = float(t.get("amount", 0))
            direction = t.get("direction", "debit")  # debit=收入, credit=支出
            counterparty = t.get("counterparty", "")
            summary = t.get("summary", "")
            bank_ref = t.get("bank_ref", "")

            db._conn.execute(
                """INSERT OR IGNORE INTO bank_transactions
                   (id, trans_date, amount, direction, counterparty, summary, bank_ref, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'unmatched')""",
                (trans_id, trans_date, amount, direction, counterparty, summary, bank_ref),
            )
            imported += 1

    return tool_result(success=True, imported=imported,
                       message=f"已导入 {imported} 笔银行流水")


def auto_reconcile(args: dict, **kwargs) -> str:
    """Auto-match bank transactions with posted voucher entries."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    _ensure_bank_table(db)
    bank_account_code = args.get("bank_account_code", "1002")

    # Get unmatched bank transactions
    with db._lock:
        cur = db._conn.execute(
            "SELECT * FROM bank_transactions WHERE status = 'unmatched' ORDER BY trans_date"
        )
        bank_trans = [dict(row) for row in cur.fetchall()]

    if not bank_trans:
        return tool_result(success=True, matched=0, unmatched=0,
                           message="没有未匹配的银行流水")

    # Get posted entries for bank account
    entries = db.get_account_details(bank_account_code)

    # Simple matching: same amount + date within 3 days
    import time
    matched_count = 0
    for bt in bank_trans:
        bt_amount = bt["amount"]
        bt_date = bt["trans_date"]

        for entry in entries:
            # Check if already matched
            if entry.get("_matched"):
                continue

            # Match amount
            entry_amount = entry["debit"] if bt["direction"] == "debit" else entry["credit"]
            if abs(entry_amount - bt_amount) > 0.01:
                continue

            # Match date (within 3 days)
            entry_date = entry.get("voucher_date", "")
            if entry_date and bt_date:
                try:
                    from datetime import datetime
                    d1 = datetime.strptime(bt_date, "%Y-%m-%d")
                    d2 = datetime.strptime(entry_date, "%Y-%m-%d")
                    if abs((d1 - d2).days) > 3:
                        continue
                except ValueError:
                    continue

            # Match found
            entry["_matched"] = True
            with db._lock:
                db._conn.execute(
                    "UPDATE bank_transactions SET status='matched', matched_voucher_id=?, matched_at=? WHERE id=?",
                    (entry["voucher_id"], time.time(), bt["id"]),
                )
            matched_count += 1
            break

    unmatched_count = len(bank_trans) - matched_count

    lines = [f"对账完成：", f"  ✅ 已匹配：{matched_count} 笔", f"  ❓ 未匹配：{unmatched_count} 笔"]
    if unmatched_count > 0:
        lines.append("  （未匹配项可能是银行已收/付但账上未记录的交易）")

    return tool_result(success=True, matched=matched_count, unmatched=unmatched_count,
                       message="\n".join(lines))


def reconciliation_status(args: dict, **kwargs) -> str:
    """Show reconciliation status — matched vs unmatched."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    _ensure_bank_table(db)

    with db._lock:
        cur = db._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM bank_transactions GROUP BY status"
        )
        stats = {row["status"]: row["cnt"] for row in cur.fetchall()}

        # Get unmatched items
        cur = db._conn.execute(
            "SELECT * FROM bank_transactions WHERE status = 'unmatched' ORDER BY trans_date LIMIT 10"
        )
        unmatched = [dict(row) for row in cur.fetchall()]

    matched = stats.get("matched", 0)
    unmatched_count = stats.get("unmatched", 0)
    total = matched + unmatched_count

    lines = [f"对账状态（共 {total} 笔银行流水）：",
             f"  ✅ 已匹配：{matched} 笔",
             f"  ❓ 未匹配：{unmatched_count} 笔"]

    if unmatched:
        lines.append("\n未匹配明细（前10笔）：")
        for u in unmatched:
            d = "收" if u["direction"] == "debit" else "付"
            lines.append(f"  {u['trans_date']} {d} {u['amount']:,.2f} {u['counterparty']} {u['summary']}")

    return tool_result(success=True, matched=matched, unmatched=unmatched_count,
                       unmatched_items=unmatched, message="\n".join(lines))


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="import_bank_transactions",
    toolset="reconciliation",
    schema={
        "name": "import_bank_transactions",
        "description": "导入银行流水数据。用户说'导入银行流水'、'录入银行对账单'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "description": "银行流水列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "交易日期 YYYY-MM-DD"},
                            "amount": {"type": "number", "description": "金额"},
                            "direction": {"type": "string", "description": "debit=收入/credit=支出"},
                            "counterparty": {"type": "string", "description": "对方户名"},
                            "summary": {"type": "string", "description": "摘要"},
                        },
                    },
                },
            },
            "required": ["transactions"],
        },
    },
    handler=import_bank_transactions,
    emoji="🏦",
)

registry.register(
    name="auto_reconcile",
    toolset="reconciliation",
    schema={
        "name": "auto_reconcile",
        "description": "自动对账——将银行流水与账上记录匹配。用户说'对账'、'核对银行流水'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "bank_account_code": {"type": "string", "description": "银行存款科目编码，默认1002"},
            },
        },
    },
    handler=auto_reconcile,
    emoji="🔄",
)

registry.register(
    name="reconciliation_status",
    toolset="reconciliation",
    schema={
        "name": "reconciliation_status",
        "description": "查看对账状态——已匹配和未匹配的流水。用户问'对账情况'、'还有多少没对上'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=reconciliation_status,
    emoji="📋",
)
