"""Period-end tools — carry-forward (期末结转) and red-letter reversal (红冲).

Toolset: "voucher"
Handles period-end closing entries and error correction via reversal.
"""

import uuid
from datetime import date
from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


def _get_current_period():
    db = _get_db()
    if not db:
        return None
    return db.get_current_period()


# =========================================================================
# Period-End Carry-Forward (期末结转)
# =========================================================================

def period_end_carryforward(args: dict, **kwargs) -> str:
    """Carry forward all income/expense accounts to '本年利润'.

    At period end, all revenue accounts (credit balance) are debited to zero,
    and all expense accounts (debit balance) are credited to zero.
    The net amount goes to '本年利润' (Retained Earnings for the Year).
    """
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    period = _get_current_period()
    if not period:
        return tool_error("没有打开的会计期间，请先创建期间")

    period_id = period["id"]

    # Find '本年利润' account (code typically starts with 3103 or 4103)
    profit_account = None
    candidates = db.search_accounts("本年利润")
    if candidates:
        profit_account = candidates[0]
    else:
        # Try common codes
        for code in ("3103", "4103"):
            acct = db.get_account(code)
            if acct:
                profit_account = acct
                break

    if not profit_account:
        return tool_error(
            "未找到「本年利润」科目。请先在科目表中添加该科目（通常编码为 3103）"
        )

    # Get all income (收入) and expense (费用/成本) leaf accounts with balances
    income_categories = ("income",)       # 收入类
    expense_categories = ("expense", "cost")  # 费用类、成本类

    entries = []
    total_income = 0.0
    total_expense = 0.0

    # Process income accounts: debit them to zero (they have credit balances)
    income_accounts = db.list_accounts(category="income")
    for acct in income_accounts:
        if not acct["is_leaf"]:
            continue
        bal_info = db.get_account_balance(acct["code"])
        # Income accounts: credit balance = credit - debit
        balance = bal_info["total_credit"] - bal_info["total_debit"]
        if abs(balance) < 0.01:
            continue
        if balance > 0:
            # Normal: income has credit balance, debit to close
            entries.append({
                "account_code": acct["code"],
                "debit": balance,
                "credit": 0,
                "summary": f"结转{acct['name']}",
            })
            total_income += balance
        else:
            # Unusual: income has debit balance
            entries.append({
                "account_code": acct["code"],
                "debit": 0,
                "credit": abs(balance),
                "summary": f"结转{acct['name']}",
            })
            total_income -= abs(balance)

    # Process expense/cost accounts: credit them to zero (they have debit balances)
    for cat in expense_categories:
        expense_accounts = db.list_accounts(category=cat)
        for acct in expense_accounts:
            if not acct["is_leaf"]:
                continue
            bal_info = db.get_account_balance(acct["code"])
            # Expense accounts: debit balance = debit - credit
            balance = bal_info["total_debit"] - bal_info["total_credit"]
            if abs(balance) < 0.01:
                continue
            if balance > 0:
                # Normal: expense has debit balance, credit to close
                entries.append({
                    "account_code": acct["code"],
                    "debit": 0,
                    "credit": balance,
                    "summary": f"结转{acct['name']}",
                })
                total_expense += balance
            else:
                # Unusual: expense has credit balance
                entries.append({
                    "account_code": acct["code"],
                    "debit": abs(balance),
                    "credit": 0,
                    "summary": f"结转{acct['name']}",
                })
                total_expense -= abs(balance)

    if not entries:
        return tool_result(
            success=True,
            message="本期没有需要结转的损益科目余额（所有收入/费用科目余额为零）。"
        )

    # Net profit = income - expense
    net_profit = total_income - total_expense

    # Add the '本年利润' entry
    if net_profit > 0:
        # Profit: credit 本年利润
        entries.append({
            "account_code": profit_account["code"],
            "debit": 0,
            "credit": net_profit,
            "summary": "结转本期损益",
        })
    elif net_profit < 0:
        # Loss: debit 本年利润
        entries.append({
            "account_code": profit_account["code"],
            "debit": abs(net_profit),
            "credit": 0,
            "summary": "结转本期损益",
        })
    else:
        # Break even — still need to balance if there are entries
        # This means income == expense, 本年利润 entry is zero, skip it
        pass

    # Verify balance
    total_debit = sum(e["debit"] for e in entries)
    total_credit = sum(e["credit"] for e in entries)
    if abs(total_debit - total_credit) > 0.01:
        return tool_error(
            f"结转计算异常：借方合计 {total_debit:.2f}，贷方合计 {total_credit:.2f}。请检查科目余额。"
        )

    # Create the carry-forward voucher
    voucher_date = args.get("date", date.today().isoformat())
    voucher_id = f"JZ{date.today().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"

    db.create_voucher(
        voucher_id=voucher_id,
        voucher_date=voucher_date,
        summary="期末结转损益",
        voucher_type="transfer",
        period_id=period_id,
    )

    for entry in entries:
        db.add_entry(
            voucher_id,
            entry["account_code"],
            debit=entry["debit"],
            credit=entry["credit"],
            summary=entry["summary"],
        )

    # Auto-post the carry-forward voucher
    db.update_voucher_status(voucher_id, "posted")

    # Build result message
    profit_label = "盈利" if net_profit >= 0 else "亏损"
    lines = [
        f"✅ 期末结转完成（{period_id}）",
        f"凭证号：{voucher_id}（已自动过账）",
        f"",
        f"结转收入：{total_income:,.2f} 元",
        f"结转费用/成本：{total_expense:,.2f} 元",
        f"本期{profit_label}：{abs(net_profit):,.2f} 元",
        f"",
        f"共结转 {len(entries) - 1} 个损益科目 → 本年利润",
    ]

    return tool_result(
        success=True,
        voucher_id=voucher_id,
        net_profit=net_profit,
        income_total=total_income,
        expense_total=total_expense,
        entry_count=len(entries),
        message="\n".join(lines),
    )


# =========================================================================
# Red-Letter Reversal (红冲)
# =========================================================================

def reverse_voucher(args: dict, **kwargs) -> str:
    """Create a red-letter reversal voucher to correct an error.

    Generates a new voucher with all amounts negated (red-letter),
    effectively canceling the original voucher's effect on the ledger.
    Optionally creates a corrected blue-letter voucher.
    """
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    original_id = args.get("voucher_id", "")
    reason = args.get("reason", "冲销错误凭证")
    correct_entries = args.get("correct_entries")  # Optional: new correct entries

    if not original_id:
        return tool_error("请指定要红冲的凭证ID")

    # Get original voucher
    original = db.get_voucher_with_entries(original_id)
    if not original:
        return tool_error(f"凭证 {original_id} 不存在")
    if original["status"] != "posted":
        return tool_error(f"凭证 {original_id} 未过账，无需红冲（可直接修改或删除草稿）")
    if not original["entries"]:
        return tool_error(f"凭证 {original_id} 没有分录")

    period = _get_current_period()
    period_id = period["id"] if period else original.get("period_id")
    voucher_date = args.get("date", date.today().isoformat())

    # --- Create red-letter (reversal) voucher ---
    red_id = f"HC{date.today().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    red_summary = f"红冲 {original_id}：{reason}"

    db.create_voucher(
        voucher_id=red_id,
        voucher_date=voucher_date,
        summary=red_summary,
        voucher_type="transfer",
        period_id=period_id,
    )

    # Reverse all entries (swap debit/credit)
    for entry in original["entries"]:
        db.add_entry(
            red_id,
            entry["account_code"],
            debit=entry["credit"],   # Swap
            credit=entry["debit"],   # Swap
            summary=f"红冲：{entry.get('summary', '')}",
        )

    # Auto-post the reversal
    db.update_voucher_status(red_id, "posted")

    result_lines = [
        f"✅ 红冲凭证 {red_id} 已创建并过账",
        f"   冲销原凭证：{original_id}（{original.get('summary', '')}）",
    ]

    # --- Optionally create corrected voucher ---
    blue_id = None
    if correct_entries and len(correct_entries) >= 2:
        # Validate balance
        total_debit = sum(e.get("debit", 0) for e in correct_entries)
        total_credit = sum(e.get("credit", 0) for e in correct_entries)
        if abs(total_debit - total_credit) > 0.01:
            result_lines.append(
                f"\n⚠️ 更正分录借贷不平衡（借 {total_debit:.2f} / 贷 {total_credit:.2f}），未创建蓝字凭证"
            )
        else:
            blue_id = f"V{date.today().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
            blue_summary = args.get("correct_summary", f"更正 {original_id}")

            db.create_voucher(
                voucher_id=blue_id,
                voucher_date=voucher_date,
                summary=blue_summary,
                voucher_type="transfer",
                period_id=period_id,
            )

            for entry in correct_entries:
                db.add_entry(
                    blue_id,
                    entry["account_code"],
                    debit=float(entry.get("debit", 0)),
                    credit=float(entry.get("credit", 0)),
                    summary=entry.get("summary", blue_summary),
                )

            db.update_voucher_status(blue_id, "posted")
            result_lines.append(f"✅ 更正凭证 {blue_id} 已创建并过账")

    return tool_result(
        success=True,
        red_voucher_id=red_id,
        blue_voucher_id=blue_id,
        original_voucher_id=original_id,
        message="\n".join(result_lines),
    )


# =========================================================================
# Tool Registration
# =========================================================================

registry.register(
    name="period_end_carryforward",
    toolset="voucher",
    schema={
        "name": "period_end_carryforward",
        "description": "期末结转损益。将所有收入和费用科目余额结转到「本年利润」。用户说'期末结转'、'结转损益'、'月末结账'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "结转凭证日期 YYYY-MM-DD，默认今天",
                },
            },
        },
    },
    handler=period_end_carryforward,
    emoji="📊",
)

registry.register(
    name="reverse_voucher",
    toolset="voucher",
    schema={
        "name": "reverse_voucher",
        "description": "红冲（红字冲销）一张已过账的凭证。用户说'红冲'、'冲销'、'那笔做错了'时使用。会生成红字凭证抵消原凭证，可选同时生成正确的蓝字凭证。",
        "parameters": {
            "type": "object",
            "properties": {
                "voucher_id": {
                    "type": "string",
                    "description": "要红冲的原凭证ID",
                },
                "reason": {
                    "type": "string",
                    "description": "红冲原因",
                },
                "date": {
                    "type": "string",
                    "description": "红冲凭证日期，默认今天",
                },
                "correct_entries": {
                    "type": "array",
                    "description": "更正后的正确分录（可选，提供则同时生成蓝字凭证）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_code": {"type": "string"},
                            "debit": {"type": "number"},
                            "credit": {"type": "number"},
                            "summary": {"type": "string"},
                        },
                        "required": ["account_code"],
                    },
                },
                "correct_summary": {
                    "type": "string",
                    "description": "更正凭证的摘要",
                },
            },
            "required": ["voucher_id"],
        },
    },
    handler=reverse_voucher,
    emoji="🔴",
)
