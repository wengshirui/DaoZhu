"""Accounting data routes — accounts, vouchers, ledger, tax, overview, todos."""

from fastapi import APIRouter

router = APIRouter()


# =========================================================================
# Accounts & Auxiliary Items & Periods
# =========================================================================

@router.get("/api/accounts")
async def get_accounts_api(category: str = None, keyword: str = None):
    """List accounts with optional filters."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"accounts": [], "error": "未选择账套"}
    if keyword:
        accounts = mgr.accounting.search_accounts(keyword)
    else:
        accounts = mgr.accounting.list_accounts(category=category)
    return {"accounts": [dict(a) for a in accounts], "count": len(accounts)}


@router.get("/api/accounts/tree")
async def get_accounts_tree():
    """Return accounts as a tree structure."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"tree": [], "error": "未选择账套"}
    accounts = mgr.accounting.list_accounts()
    by_code = {a["code"]: {**a, "children": []} for a in accounts}
    tree = []
    for a in accounts:
        node = by_code[a["code"]]
        parent = a.get("parent_code")
        if parent and parent in by_code:
            by_code[parent]["children"].append(node)
        else:
            tree.append(node)
    return {"tree": tree}


@router.get("/api/aux-items")
async def get_aux_items_api(type: str = None):
    """List auxiliary accounting items."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"items": [], "error": "未选择账套"}
    with mgr.accounting._lock:
        sql = "SELECT * FROM aux_items WHERE is_active = 1"
        params = []
        if type:
            sql += " AND type = ?"
            params.append(type)
        sql += " ORDER BY type, code"
        cur = mgr.accounting._conn.execute(sql, params)
        items = [dict(row) for row in cur.fetchall()]
    return {"items": items, "count": len(items)}


@router.get("/api/periods")
async def get_periods_api():
    """List accounting periods."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"periods": [], "error": "未选择账套"}
    periods = mgr.accounting.list_periods()
    return {"periods": [dict(p) for p in periods], "count": len(periods)}


# =========================================================================
# Data Overview
# =========================================================================

@router.get("/api/data/overview")
async def data_overview():
    """Return key financial metrics for the left panel data display."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"error": "选择账套后显示数据"}

    db = mgr.accounting

    # Bank balance (code starts with 1002)
    bank_balance = 0.0
    bank_accounts = [a for a in db.list_accounts() if a["code"].startswith("1002") and a["is_leaf"]]
    for acct in bank_accounts:
        bal = db.get_account_balance(acct["code"])
        bank_balance += bal["balance"]

    # Receivable (1122)
    receivable = 0.0
    recv_accounts = [a for a in db.list_accounts() if a["code"].startswith("1122") and a["is_leaf"]]
    for acct in recv_accounts:
        bal = db.get_account_balance(acct["code"])
        receivable += bal["balance"]

    # Payable (2202)
    payable = 0.0
    pay_accounts = [a for a in db.list_accounts() if a["code"].startswith("2202") and a["is_leaf"]]
    for acct in pay_accounts:
        bal = db.get_account_balance(acct["code"])
        payable += bal["balance"]

    # Monthly income/expense
    from datetime import date as date_mod
    today = date_mod.today()
    period_id = f"{today.year}-{today.month:02d}"
    month_start = f"{today.year}-{today.month:02d}-01"
    month_end = f"{today.year}-{today.month:02d}-31"

    monthly_income = 0.0
    monthly_expense = 0.0

    with db._lock:
        cur = db._conn.execute("""
            SELECT COALESCE(SUM(e.credit - e.debit), 0) as total
            FROM entries e
            JOIN vouchers v ON e.voucher_id = v.id
            JOIN accounts a ON e.account_code = a.code
            WHERE v.status = 'posted'
              AND a.category = 'income'
              AND v.voucher_date >= ? AND v.voucher_date <= ?
        """, (month_start, month_end))
        row = cur.fetchone()
        monthly_income = row["total"] if row else 0.0

        cur = db._conn.execute("""
            SELECT COALESCE(SUM(e.debit - e.credit), 0) as total
            FROM entries e
            JOIN vouchers v ON e.voucher_id = v.id
            JOIN accounts a ON e.account_code = a.code
            WHERE v.status = 'posted'
              AND a.category = 'expense'
              AND v.voucher_date >= ? AND v.voucher_date <= ?
        """, (month_start, month_end))
        row = cur.fetchone()
        monthly_expense = row["total"] if row else 0.0

    # Draft voucher count
    drafts = db.list_vouchers(status="draft", limit=999)
    draft_count = len(drafts)

    # Degraded detection
    degraded = False
    degraded_reasons = []

    with db._lock:
        posted_count = db._conn.execute(
            "SELECT COUNT(*) FROM vouchers WHERE status = 'posted'"
        ).fetchone()[0]
    if posted_count == 0:
        degraded = True
        degraded_reasons.append("无已过账凭证，数据为空")
    elif monthly_income == 0 and monthly_expense == 0:
        with db._lock:
            month_posted = db._conn.execute(
                "SELECT COUNT(*) FROM vouchers WHERE status = 'posted' AND voucher_date >= ? AND voucher_date <= ?",
                (month_start, month_end),
            ).fetchone()[0]
        if month_posted == 0:
            degraded = True
            degraded_reasons.append(f"本月（{period_id}）无已过账凭证")

    current_period = db.get_current_period()
    if not current_period:
        degraded = True
        degraded_reasons.append("未设置会计期间")

    return {
        "bank_balance": bank_balance,
        "receivable": receivable,
        "payable": payable,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "draft_count": draft_count,
        "period": period_id,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
    }


# =========================================================================
# Vouchers
# =========================================================================

@router.get("/api/vouchers")
async def list_vouchers_api(
    period_id: str = None,
    status: str = None,
    keyword: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50,
    offset: int = 0,
):
    """List vouchers with filtering for the business panel."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"vouchers": [], "error": "未选择账套", "total": 0}

    db = mgr.accounting
    with db._lock:
        sql = "SELECT * FROM vouchers WHERE 1=1"
        params = []

        if period_id:
            sql += " AND period_id = ?"
            params.append(period_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if keyword:
            sql += " AND summary LIKE ?"
            params.append(f"%{keyword}%")
        if date_from:
            sql += " AND voucher_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND voucher_date <= ?"
            params.append(date_to)

        count_sql = sql.replace("SELECT *", "SELECT COUNT(*)")
        cur = db._conn.execute(count_sql, params)
        total = cur.fetchone()[0]

        sql += " ORDER BY voucher_date DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cur = db._conn.execute(sql, params)
        vouchers = [dict(row) for row in cur.fetchall()]

    for v in vouchers:
        entries = db.get_voucher_with_entries(v["id"])
        if entries:
            v["entry_count"] = len(entries.get("entries", []))
            v["total_debit"] = sum(e["debit"] for e in entries.get("entries", []))
        else:
            v["entry_count"] = 0
            v["total_debit"] = 0

    return {"vouchers": vouchers, "total": total, "limit": limit, "offset": offset}


@router.get("/api/vouchers/{voucher_id}")
async def get_voucher_detail_api(voucher_id: str):
    """Get voucher detail with all entries."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"error": "未选择账套"}

    voucher = mgr.accounting.get_voucher_with_entries(voucher_id)
    if not voucher:
        return {"error": f"凭证 {voucher_id} 不存在"}

    for entry in voucher.get("entries", []):
        account = mgr.accounting.get_account(entry["account_code"])
        entry["account_name"] = account["name"] if account else entry["account_code"]

    return {"voucher": voucher}


# =========================================================================
# Tax Summary
# =========================================================================

@router.get("/api/tax/summary")
async def get_tax_summary():
    """Return tax summary for the overview panel."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"error": "未选择账套"}

    db = mgr.accounting
    total_tax = 0.0
    details = []

    with db._lock:
        cur = db._conn.execute(
            "SELECT code, name FROM accounts WHERE code LIKE '2221%' AND is_active = 1 ORDER BY code"
        )
        tax_accounts = [dict(row) for row in cur.fetchall()]

    for acct in tax_accounts:
        bal = db.get_account_balance(acct["code"])
        if bal["balance"] != 0 or bal["total_debit"] != 0 or bal["total_credit"] != 0:
            details.append({
                "code": acct["code"],
                "name": acct["name"],
                "balance": round(bal["balance"], 2),
            })
            if acct["code"] == "2221":
                has_children = any(a["code"] != "2221" for a in tax_accounts)
                if not has_children:
                    total_tax += bal["balance"]
            else:
                total_tax += bal["balance"]

    return {"total_tax": round(total_tax, 2), "details": details}


# =========================================================================
# Ledger / Trial Balance
# =========================================================================

@router.get("/api/ledger/balance-sheet")
async def get_balance_sheet_api(period_id: str = None, category: str = None):
    """Get trial balance (科目余额表) for the business panel."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"accounts": [], "error": "未选择账套"}

    db = mgr.accounting
    accounts = db.list_accounts(category=category)
    result = []

    for acct in accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_debit"] == 0 and bal["total_credit"] == 0:
            continue
        result.append({
            "code": acct["code"],
            "name": acct["name"],
            "category": acct["category"],
            "direction": bal["direction"],
            "total_debit": bal["total_debit"],
            "total_credit": bal["total_credit"],
            "balance": bal["balance"],
        })

    # Degraded detection
    degraded = False
    degraded_reasons = []

    if not result:
        with db._lock:
            posted = db._conn.execute(
                "SELECT COUNT(*) FROM vouchers WHERE status = 'posted'"
            ).fetchone()[0]
            draft = db._conn.execute(
                "SELECT COUNT(*) FROM vouchers WHERE status = 'draft'"
            ).fetchone()[0]
        if draft > 0 and posted == 0:
            degraded = True
            degraded_reasons.append(f"有 {draft} 张草稿凭证未过账，过账后才会显示余额")

    current_period = db.get_current_period()
    if not current_period:
        degraded = True
        degraded_reasons.append("未设置会计期间，余额为全部期间累计")

    return {
        "accounts": result,
        "count": len(result),
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
    }


@router.get("/api/ledger/account-detail/{account_code}")
async def get_account_detail_api(account_code: str, period_id: str = None):
    """Get detailed balance breakdown for a single account (期初/本期借方/本期贷方/期末)."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"error": "未选择账套"}

    db = mgr.accounting

    if not period_id:
        period = db.get_current_period()
        period_id = period["id"] if period else None

    acct_row = db._conn.execute(
        "SELECT code, name, category, balance_direction FROM accounts WHERE code = ?",
        (account_code,),
    ).fetchone()
    if not acct_row:
        return {"error": "科目不存在"}

    direction = acct_row["balance_direction"]

    period_sql = """SELECT COALESCE(SUM(e.debit), 0) as period_debit,
                           COALESCE(SUM(e.credit), 0) as period_credit
                    FROM entries e
                    JOIN vouchers v ON e.voucher_id = v.id
                    WHERE e.account_code = ? AND v.status = 'posted'"""
    period_params = [account_code]
    if period_id:
        period_sql += " AND v.period_id = ?"
        period_params.append(period_id)

    cur = db._conn.execute(period_sql, period_params)
    row = cur.fetchone()
    period_debit = row["period_debit"]
    period_credit = row["period_credit"]

    opening_balance = 0.0
    if period_id:
        open_sql = """SELECT COALESCE(SUM(e.debit), 0) as d,
                             COALESCE(SUM(e.credit), 0) as c
                      FROM entries e
                      JOIN vouchers v ON e.voucher_id = v.id
                      WHERE e.account_code = ? AND v.status = 'posted'
                        AND v.period_id < ?"""
        open_row = db._conn.execute(open_sql, [account_code, period_id]).fetchone()
        if direction == "debit":
            opening_balance = open_row["d"] - open_row["c"]
        else:
            opening_balance = open_row["c"] - open_row["d"]

    if direction == "debit":
        closing_balance = opening_balance + period_debit - period_credit
    else:
        closing_balance = opening_balance + period_credit - period_debit

    # Degraded detection
    degraded = False
    degraded_reasons = []
    if not period_id:
        degraded = True
        degraded_reasons.append("未设置会计期间，显示全部累计数据")
    elif period_debit == 0 and period_credit == 0 and opening_balance == 0:
        degraded = True
        degraded_reasons.append(f"该科目在期间 {period_id} 无任何发生额")

    return {
        "code": acct_row["code"],
        "name": acct_row["name"],
        "category": acct_row["category"],
        "direction": direction,
        "period_id": period_id,
        "opening_balance": opening_balance,
        "period_debit": period_debit,
        "period_credit": period_credit,
        "closing_balance": closing_balance,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
    }


