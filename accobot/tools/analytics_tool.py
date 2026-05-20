"""Data analytics tools — expense breakdown, trends, anomaly detection.

Toolset: "analytics"
Provides financial analysis capabilities through natural language.
"""

from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


def expense_breakdown(args: dict, **kwargs) -> str:
    """Analyze expense structure — which categories cost the most."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    expense_accounts = db.list_accounts(category="expense")
    items = []
    total = 0.0

    for acct in expense_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["balance"] > 0:
            items.append({"name": acct["name"], "code": acct["code"], "amount": bal["balance"]})
            total += bal["balance"]

    if not items:
        return tool_result(success=True, items=[], message="暂无费用数据（没有已过账的费用凭证）")

    # Sort by amount descending
    items.sort(key=lambda x: x["amount"], reverse=True)

    # Calculate percentages
    for item in items:
        item["percent"] = round(item["amount"] / total * 100, 1) if total > 0 else 0

    lines = [f"费用结构分析（总计 {total:,.2f} 元）：", ""]
    for i, item in enumerate(items[:10], 1):
        bar = "█" * int(item["percent"] / 5) if item["percent"] >= 5 else "▏"
        lines.append(f"  {i}. {item['name']:<12} {item['amount']:>10,.2f}  {item['percent']:>5.1f}%  {bar}")

    if len(items) > 10:
        others = sum(x["amount"] for x in items[10:])
        lines.append(f"  ...其他 {len(items)-10} 项  {others:>10,.2f}")

    return tool_result(success=True, items=items, total=total, message="\n".join(lines))


def revenue_vs_expense(args: dict, **kwargs) -> str:
    """Compare total revenue vs total expenses."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    # Revenue
    revenue_accounts = db.list_accounts(category="income")
    total_revenue = 0.0
    for acct in revenue_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        total_revenue += bal["balance"]

    # Expenses
    expense_accounts = db.list_accounts(category="expense")
    total_expense = 0.0
    for acct in expense_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        total_expense += bal["balance"]

    # Cost
    cost_accounts = db.list_accounts(category="cost")
    total_cost = 0.0
    for acct in cost_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        total_cost += bal["balance"]

    net = total_revenue - total_expense - total_cost
    status = "盈利 ✅" if net > 0 else ("亏损 ⚠️" if net < 0 else "持平")

    lines = [
        "收支对比分析：",
        f"  📈 收入合计：{total_revenue:>12,.2f}",
        f"  📉 成本合计：{total_cost:>12,.2f}",
        f"  📉 费用合计：{total_expense:>12,.2f}",
        "─" * 30,
        f"  💰 净利润：  {net:>12,.2f}  （{status}）",
    ]

    if total_revenue > 0:
        margin = net / total_revenue * 100
        lines.append(f"  📊 净利率：  {margin:.1f}%")

    return tool_result(
        success=True,
        revenue=total_revenue, cost=total_cost, expense=total_expense,
        net_profit=net, status=status,
        message="\n".join(lines),
    )


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="expense_breakdown",
    toolset="analytics",
    schema={
        "name": "expense_breakdown",
        "description": "费用结构分析——看钱花在哪了。用户问'钱花在哪了'、'费用分析'、'哪项费用最多'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=expense_breakdown,
    emoji="📊",
)

registry.register(
    name="revenue_vs_expense",
    toolset="analytics",
    schema={
        "name": "revenue_vs_expense",
        "description": "收支对比分析——收入和支出的总体情况。用户问'赚了多少'、'收支情况'、'是盈利还是亏损'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=revenue_vs_expense,
    emoji="💰",
)
