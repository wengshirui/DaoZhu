"""Voucher & Journal Entry tools — create vouchers, generate entries, post.

Toolset: "voucher"
Handles the full voucher lifecycle: create → add entries → review → post.
AI can suggest journal entries based on business description.
"""

import json
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
# Voucher CRUD
# =========================================================================

def create_voucher(args: dict, **kwargs) -> str:
    """Create a new voucher (draft)."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    voucher_date = args.get("date", date.today().isoformat())
    summary = args.get("summary", "")
    voucher_type = args.get("type", "transfer")

    if not summary:
        return tool_error("请提供凭证摘要（这笔钱是做什么的）")

    # Determine period
    period = _get_current_period()
    period_id = period["id"] if period else None

    voucher_id = f"V{date.today().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"

    result = db.create_voucher(
        voucher_id=voucher_id,
        voucher_date=voucher_date,
        summary=summary,
        voucher_type=voucher_type,
        period_id=period_id,
    )

    return tool_result(
        success=True,
        voucher_id=voucher_id,
        date=voucher_date,
        summary=summary,
        status="draft",
        message=f"已创建凭证草稿 {voucher_id}：{voucher_date} {summary}",
    )


def add_entry(args: dict, **kwargs) -> str:
    """Add a journal entry line to a voucher."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    voucher_id = args.get("voucher_id", "")
    account_code = args.get("account_code", "")
    debit = args.get("debit", 0)
    credit = args.get("credit", 0)
    summary = args.get("summary", "")

    if not voucher_id:
        return tool_error("请指定凭证ID")
    if not account_code:
        return tool_error("请指定科目编码")
    if debit == 0 and credit == 0:
        return tool_error("借方或贷方金额不能都为0")
    if debit != 0 and credit != 0:
        return tool_error("一条分录只能填借方或贷方，不能同时填")

    # Verify account exists
    account = db.get_account(account_code)
    if not account:
        return tool_error(f"科目 {account_code} 不存在")

    entry_id = db.add_entry(
        voucher_id=voucher_id,
        account_code=account_code,
        debit=float(debit),
        credit=float(credit),
        summary=summary,
    )

    direction = "借" if debit > 0 else "贷"
    amount = debit if debit > 0 else credit

    return tool_result(
        success=True,
        entry_id=entry_id,
        message=f"  {direction}：{account['name']}（{account_code}）{amount:.2f}",
    )


def create_voucher_with_entries(args: dict, **kwargs) -> str:
    """Create a complete voucher with entries in one call.

    This is the primary tool for recording transactions. The AI should use this
    to create a voucher with all debit/credit entries at once.
    """
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    voucher_date = args.get("date", date.today().isoformat())
    summary = args.get("summary", "")
    entries = args.get("entries", [])

    if not summary:
        return tool_error("请提供凭证摘要")
    if not entries or len(entries) < 2:
        return tool_error("至少需要一借一贷两条分录")

    # Validate balance
    total_debit = sum(e.get("debit", 0) for e in entries)
    total_credit = sum(e.get("credit", 0) for e in entries)
    if abs(total_debit - total_credit) > 0.01:
        return tool_error(f"借贷不平衡：借方 {total_debit:.2f}，贷方 {total_credit:.2f}，差额 {abs(total_debit - total_credit):.2f}")

    # Validate all accounts exist
    for i, entry in enumerate(entries):
        code = entry.get("account_code", "")
        if not code:
            return tool_error(f"第{i+1}条分录缺少科目编码")
        account = db.get_account(code)
        if not account:
            return tool_error(f"科目 {code} 不存在")

    # Create voucher
    period = _get_current_period()
    period_id = period["id"] if period else None
    voucher_id = f"V{date.today().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"

    db.create_voucher(
        voucher_id=voucher_id,
        voucher_date=voucher_date,
        summary=summary,
        period_id=period_id,
    )

    # Add entries
    entry_lines = []
    for entry in entries:
        code = entry["account_code"]
        debit = float(entry.get("debit", 0))
        credit = float(entry.get("credit", 0))
        entry_summary = entry.get("summary", summary)
        db.add_entry(voucher_id, code, debit=debit, credit=credit, summary=entry_summary)

        account = db.get_account(code)
        direction = "借" if debit > 0 else "贷"
        amount = debit if debit > 0 else credit
        entry_lines.append(f"  {direction}：{account['name']} {amount:,.2f}")

    msg = f"✅ 凭证 {voucher_id} 已创建（{voucher_date} {summary}）\n" + "\n".join(entry_lines)
    return tool_result(success=True, voucher_id=voucher_id, message=msg)


def query_vouchers(args: dict, **kwargs) -> str:
    """Query vouchers by period or status."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    period_id = args.get("period_id")
    status = args.get("status")
    limit = args.get("limit", 20)

    vouchers = db.list_vouchers(period_id=period_id, status=status, limit=limit)

    if not vouchers:
        return tool_result(success=True, vouchers=[], message="未找到凭证")

    items = []
    for v in vouchers:
        items.append({
            "id": v["id"], "date": v["voucher_date"],
            "summary": v["summary"], "status": v["status"],
        })

    return tool_result(success=True, vouchers=items, count=len(items),
                       message=f"找到 {len(items)} 张凭证")


def get_voucher_detail(args: dict, **kwargs) -> str:
    """Get a voucher with all its entries."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    voucher_id = args.get("voucher_id", "")
    if not voucher_id:
        return tool_error("请指定凭证ID")

    voucher = db.get_voucher_with_entries(voucher_id)
    if not voucher:
        return tool_error(f"凭证 {voucher_id} 不存在")

    lines = [f"凭证 {voucher['id']}（{voucher['voucher_date']} {voucher['summary']}）状态：{voucher['status']}"]
    for e in voucher["entries"]:
        account = db.get_account(e["account_code"])
        name = account["name"] if account else e["account_code"]
        if e["debit"] > 0:
            lines.append(f"  借：{name}  {e['debit']:,.2f}")
        if e["credit"] > 0:
            lines.append(f"  贷：{name}  {e['credit']:,.2f}")

    return tool_result(success=True, voucher=voucher, message="\n".join(lines))


def post_voucher(args: dict, **kwargs) -> str:
    """Post a voucher (change status from draft to posted)."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    voucher_id = args.get("voucher_id", "")
    if not voucher_id:
        return tool_error("请指定凭证ID")

    voucher = db.get_voucher_with_entries(voucher_id)
    if not voucher:
        return tool_error(f"凭证 {voucher_id} 不存在")
    if voucher["status"] == "posted":
        return tool_error(f"凭证 {voucher_id} 已经过账")
    if not voucher["entries"]:
        return tool_error(f"凭证 {voucher_id} 没有分录，无法过账")

    # Validate balance
    total_debit = sum(e["debit"] for e in voucher["entries"])
    total_credit = sum(e["credit"] for e in voucher["entries"])
    if abs(total_debit - total_credit) > 0.01:
        return tool_error(f"借贷不平衡，无法过账：借方 {total_debit:.2f}，贷方 {total_credit:.2f}")

    db.update_voucher_status(voucher_id, "posted")
    return tool_result(success=True, message=f"✅ 凭证 {voucher_id} 已过账")


# =========================================================================
# Tool Registration
# =========================================================================

registry.register(
    name="create_voucher_with_entries",
    toolset="voucher",
    schema={
        "name": "create_voucher_with_entries",
        "description": "创建一张完整的记账凭证（含借贷分录）。用户说'记一笔'、'付了XX钱'、'收到货款'等时使用。这是最常用的记账工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "凭证日期 YYYY-MM-DD，默认今天"},
                "summary": {"type": "string", "description": "摘要，如：付房租、收货款"},
                "entries": {
                    "type": "array",
                    "description": "分录列表，至少一借一贷",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_code": {"type": "string", "description": "科目编码"},
                            "debit": {"type": "number", "description": "借方金额（与credit二选一）"},
                            "credit": {"type": "number", "description": "贷方金额（与debit二选一）"},
                            "summary": {"type": "string", "description": "分录摘要（可选）"},
                        },
                        "required": ["account_code"],
                    },
                },
            },
            "required": ["summary", "entries"],
        },
    },
    handler=create_voucher_with_entries,
    emoji="📝",
)

registry.register(
    name="query_vouchers",
    toolset="voucher",
    schema={
        "name": "query_vouchers",
        "description": "查询凭证列表。用户问'这个月的凭证'、'有哪些未过账的凭证'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "period_id": {"type": "string", "description": "期间ID如2026-05"},
                "status": {"type": "string", "description": "状态筛选：draft/posted"},
                "limit": {"type": "integer", "description": "返回数量上限"},
            },
        },
    },
    handler=query_vouchers,
    emoji="🔍",
)

registry.register(
    name="get_voucher_detail",
    toolset="voucher",
    schema={
        "name": "get_voucher_detail",
        "description": "查看一张凭证的详细信息（含所有分录）。",
        "parameters": {
            "type": "object",
            "properties": {
                "voucher_id": {"type": "string", "description": "凭证ID"},
            },
            "required": ["voucher_id"],
        },
    },
    handler=get_voucher_detail,
    emoji="📋",
)

registry.register(
    name="post_voucher",
    toolset="voucher",
    schema={
        "name": "post_voucher",
        "description": "过账（将凭证从草稿变为已过账，写入账簿）。用户说'过账'、'确认这张凭证'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "voucher_id": {"type": "string", "description": "凭证ID"},
            },
            "required": ["voucher_id"],
        },
    },
    handler=post_voucher,
    emoji="✅",
)
