"""Ledger query tools — account balances and transaction details.

Toolset: "ledger"
Query account balances, detail records, and trial balance.
"""

import json
from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


def query_balance(args: dict, **kwargs) -> str:
    """Query account balance by name or code."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    account_name = args.get("account_name", "")
    account_code = args.get("account_code", "")

    if not account_name and not account_code:
        return tool_error("请指定科目名称或编码")

    # Find account
    if account_code:
        account = db.get_account(account_code)
        if not account:
            return tool_error(f"科目 {account_code} 不存在")
    else:
        results = db.search_accounts(account_name)
        if not results:
            return tool_error(f"未找到科目「{account_name}」")
        account = results[0]  # Take best match

    balance_info = db.get_account_balance(account["code"])

    direction_label = "借方" if balance_info["direction"] == "debit" else "贷方"
    msg = (f"科目：{account['name']}（{account['code']}）\n"
           f"余额：{balance_info['balance']:,.2f} 元（{direction_label}）\n"
           f"累计借方：{balance_info['total_debit']:,.2f}  累计贷方：{balance_info['total_credit']:,.2f}")

    return tool_result(
        success=True,
        account_code=account["code"],
        account_name=account["name"],
        balance=balance_info["balance"],
        direction=balance_info["direction"],
        total_debit=balance_info["total_debit"],
        total_credit=balance_info["total_credit"],
        message=msg,
    )


def query_detail(args: dict, **kwargs) -> str:
    """Query account detail records."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    account_name = args.get("account_name", "")
    account_code = args.get("account_code", "")
    period_id = args.get("period_id")

    if not account_name and not account_code:
        return tool_error("请指定科目名称或编码")

    # Find account
    if account_code:
        account = db.get_account(account_code)
    else:
        results = db.search_accounts(account_name)
        if not results:
            return tool_error(f"未找到科目「{account_name}」")
        account = results[0]

    if not account:
        return tool_error(f"科目不存在")

    details = db.get_account_details(account["code"], period_id=period_id)

    if not details:
        return tool_result(success=True, records=[], message=f"科目「{account['name']}」暂无明细记录")

    lines = [f"科目「{account['name']}」明细（共 {len(details)} 笔）："]
    running = 0.0
    for d in details[:20]:  # Limit display
        amount_debit = d["debit"]
        amount_credit = d["credit"]
        running += amount_debit - amount_credit
        date_str = d.get("voucher_date", "")
        summary = d.get("summary", "") or d.get("voucher_summary", "")
        if amount_debit > 0:
            lines.append(f"  {date_str} {summary}  借 {amount_debit:,.2f}  余额 {running:,.2f}")
        else:
            lines.append(f"  {date_str} {summary}  贷 {amount_credit:,.2f}  余额 {running:,.2f}")

    if len(details) > 20:
        lines.append(f"  ...（还有 {len(details) - 20} 笔未显示）")

    return tool_result(success=True, records=details[:20], count=len(details), message="\n".join(lines))


def trial_balance(args: dict, **kwargs) -> str:
    """Get trial balance (科目余额表) for all accounts with activity."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    accounts = db.list_accounts()
    balances = []

    for acct in accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        if bal["total_debit"] == 0 and bal["total_credit"] == 0:
            continue
        balances.append({
            "code": acct["code"],
            "name": acct["name"],
            "debit": bal["total_debit"],
            "credit": bal["total_credit"],
            "balance": bal["balance"],
            "direction": bal["direction"],
        })

    if not balances:
        return tool_result(success=True, balances=[], message="暂无科目发生额（还没有过账的凭证）")

    lines = ["科目余额表：", f"{'编码':<8}{'科目名称':<12}{'借方发生':>12}{'贷方发生':>12}{'余额':>12}"]
    lines.append("-" * 56)
    for b in balances:
        lines.append(f"{b['code']:<8}{b['name']:<12}{b['debit']:>12,.2f}{b['credit']:>12,.2f}{b['balance']:>12,.2f}")

    return tool_result(success=True, balances=balances, count=len(balances), message="\n".join(lines))


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="query_balance",
    toolset="ledger",
    schema={
        "name": "query_balance",
        "description": "查询科目余额。用户问'银行存款还有多少'、'应收账款余额'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string", "description": "科目名称（模糊匹配）"},
                "account_code": {"type": "string", "description": "科目编码（精确）"},
            },
        },
    },
    handler=query_balance,
    emoji="📊",
)

registry.register(
    name="query_detail",
    toolset="ledger",
    schema={
        "name": "query_detail",
        "description": "查询科目明细账。用户问'管理费用明细'、'这个月银行存款流水'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string", "description": "科目名称"},
                "account_code": {"type": "string", "description": "科目编码"},
                "period_id": {"type": "string", "description": "期间如2026-05"},
            },
        },
    },
    handler=query_detail,
    emoji="📋",
)

registry.register(
    name="trial_balance",
    toolset="ledger",
    schema={
        "name": "trial_balance",
        "description": "生成科目余额表（所有有发生额的科目汇总）。用户问'科目余额表'、'各科目余额'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=trial_balance,
    emoji="📊",
)
