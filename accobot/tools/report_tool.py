"""Financial report tools — Balance Sheet, Income Statement.

Toolset: "report"
Generates standard financial reports from posted voucher data.
"""

from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


def _sum_balances(db, category: str, codes_prefix: list = None) -> float:
    """Sum balances for accounts in a category or with specific code prefixes."""
    accounts = db.list_accounts(category=category)
    total = 0.0
    for acct in accounts:
        if not acct["is_leaf"]:
            continue
        if codes_prefix:
            if not any(acct["code"].startswith(p) for p in codes_prefix):
                continue
        bal = db.get_account_balance(acct["code"])
        total += bal["balance"]
    return total


def income_statement(args: dict, **kwargs) -> str:
    """Generate income statement (利润表)."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    # Revenue (收入类科目余额 = 贷方余额)
    revenue_accounts = db.list_accounts(category="income")
    total_revenue = 0.0
    revenue_detail = []
    for acct in revenue_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_credit"] > 0 or bal["total_debit"] > 0:
            amount = bal["balance"]  # credit direction, so balance is positive for revenue
            total_revenue += amount
            revenue_detail.append({"name": acct["name"], "amount": amount})

    # Expenses (费用类科目余额 = 借方余额)
    expense_accounts = db.list_accounts(category="expense")
    total_expense = 0.0
    expense_detail = []
    for acct in expense_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_debit"] > 0 or bal["total_credit"] > 0:
            amount = bal["balance"]
            total_expense += amount
            expense_detail.append({"name": acct["name"], "amount": amount})

    # Cost (成本类)
    cost_accounts = db.list_accounts(category="cost")
    total_cost = 0.0
    for acct in cost_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_debit"] > 0:
            total_cost += bal["balance"]

    net_profit = total_revenue - total_expense - total_cost

    # Format output
    lines = ["═══ 利润表 ═══", ""]
    lines.append(f"一、营业收入          {total_revenue:>12,.2f}")
    for r in revenue_detail:
        lines.append(f"    {r['name']:<16}{r['amount']:>12,.2f}")
    lines.append(f"二、营业成本          {total_cost:>12,.2f}")
    lines.append(f"三、期间费用          {total_expense:>12,.2f}")
    for e in expense_detail[:10]:
        lines.append(f"    {e['name']:<16}{e['amount']:>12,.2f}")
    if len(expense_detail) > 10:
        lines.append(f"    ...（还有 {len(expense_detail)-10} 项）")
    lines.append("─" * 40)
    lines.append(f"四、净利润            {net_profit:>12,.2f}")

    return tool_result(
        success=True,
        revenue=total_revenue,
        cost=total_cost,
        expense=total_expense,
        net_profit=net_profit,
        revenue_detail=revenue_detail,
        expense_detail=expense_detail,
        message="\n".join(lines),
    )


def balance_sheet(args: dict, **kwargs) -> str:
    """Generate balance sheet (资产负债表)."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    # Assets
    asset_accounts = db.list_accounts(category="asset")
    total_assets = 0.0
    asset_items = []
    for acct in asset_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_debit"] > 0 or bal["total_credit"] > 0:
            total_assets += bal["balance"]
            asset_items.append({"name": acct["name"], "amount": bal["balance"]})

    # Liabilities
    liability_accounts = db.list_accounts(category="liability")
    total_liabilities = 0.0
    liability_items = []
    for acct in liability_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_debit"] > 0 or bal["total_credit"] > 0:
            total_liabilities += bal["balance"]
            liability_items.append({"name": acct["name"], "amount": bal["balance"]})

    # Equity
    equity_accounts = db.list_accounts(category="equity")
    total_equity = 0.0
    equity_items = []
    for acct in equity_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_debit"] > 0 or bal["total_credit"] > 0:
            total_equity += bal["balance"]
            equity_items.append({"name": acct["name"], "amount": bal["balance"]})

    total_liab_equity = total_liabilities + total_equity
    balanced = abs(total_assets - total_liab_equity) < 0.01

    lines = ["═══ 资产负债表 ═══", ""]
    lines.append("【资产】")
    for item in asset_items[:15]:
        lines.append(f"  {item['name']:<18}{item['amount']:>12,.2f}")
    lines.append(f"  {'资产合计':<18}{total_assets:>12,.2f}")
    lines.append("")
    lines.append("【负债】")
    for item in liability_items[:10]:
        lines.append(f"  {item['name']:<18}{item['amount']:>12,.2f}")
    lines.append(f"  {'负债合计':<18}{total_liabilities:>12,.2f}")
    lines.append("")
    lines.append("【所有者权益】")
    for item in equity_items[:5]:
        lines.append(f"  {item['name']:<18}{item['amount']:>12,.2f}")
    lines.append(f"  {'权益合计':<18}{total_equity:>12,.2f}")
    lines.append("─" * 40)
    lines.append(f"  {'负债+权益合计':<14}{total_liab_equity:>12,.2f}")
    if not balanced:
        lines.append(f"  ⚠️ 不平衡！差额：{total_assets - total_liab_equity:,.2f}")

    return tool_result(
        success=True,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        balanced=balanced,
        message="\n".join(lines),
    )


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="income_statement",
    toolset="report",
    schema={
        "name": "income_statement",
        "description": "生成利润表。用户问'利润表'、'这个月赚了多少'、'收入支出情况'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=income_statement,
    emoji="📈",
)

registry.register(
    name="balance_sheet",
    toolset="report",
    schema={
        "name": "balance_sheet",
        "description": "生成资产负债表。用户问'资产负债表'、'公司有多少资产'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=balance_sheet,
    emoji="📊",
)
