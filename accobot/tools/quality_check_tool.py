"""Quality check & risk control tools.

Toolset: "quality"
Checks vouchers and operations for compliance risks.
"""

from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


def check_vouchers(args: dict, **kwargs) -> str:
    """Run quality checks on vouchers — find issues and risks."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    period_id = args.get("period_id")
    vouchers = db.list_vouchers(period_id=period_id, limit=200)

    if not vouchers:
        return tool_result(success=True, issues=[], message="没有凭证需要检查")

    issues = []

    for v in vouchers:
        voucher = db.get_voucher_with_entries(v["id"])
        if not voucher:
            continue
        entries = voucher.get("entries", [])

        # Check 1: Balance
        total_debit = sum(e["debit"] for e in entries)
        total_credit = sum(e["credit"] for e in entries)
        if abs(total_debit - total_credit) > 0.01:
            issues.append({
                "level": "critical",
                "icon": "🔴",
                "voucher_id": v["id"],
                "message": f"借贷不平衡：借方 {total_debit:.2f}，贷方 {total_credit:.2f}",
            })

        # Check 2: Empty summary
        if not voucher.get("summary"):
            issues.append({
                "level": "warning",
                "icon": "🟡",
                "voucher_id": v["id"],
                "message": "凭证摘要为空",
            })

        # Check 3: Large amount (>50000 cash)
        for e in entries:
            if e["account_code"] == "1001" and (e["debit"] > 50000 or e["credit"] > 50000):
                issues.append({
                    "level": "warning",
                    "icon": "🟡",
                    "voucher_id": v["id"],
                    "message": f"大额现金交易 {max(e['debit'], e['credit']):,.2f} 元，请确认合规性",
                })

        # Check 4: No entries
        if not entries:
            issues.append({
                "level": "critical",
                "icon": "🔴",
                "voucher_id": v["id"],
                "message": "凭证没有分录",
            })

    # Check 5: Voucher number gaps
    # (simplified — just count)
    draft_count = sum(1 for v in vouchers if v["status"] == "draft")
    if draft_count > 10:
        issues.append({
            "level": "info",
            "icon": "🟢",
            "voucher_id": "",
            "message": f"有 {draft_count} 张凭证处于草稿状态，建议及时审核过账",
        })

    # Check 6: Account direction anomaly
    accounts = db.list_accounts()
    for acct in accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        # Asset with credit balance or liability with debit balance
        if acct["category"] == "asset" and bal["balance"] < -0.01:
            issues.append({
                "level": "warning",
                "icon": "🟡",
                "voucher_id": "",
                "message": f"资产科目「{acct['name']}」出现贷方余额 {bal['balance']:,.2f}，请检查",
            })
        elif acct["category"] == "liability" and bal["balance"] < -0.01:
            issues.append({
                "level": "warning",
                "icon": "🟡",
                "voucher_id": "",
                "message": f"负债科目「{acct['name']}」出现借方余额，请检查",
            })

    # Format output
    if not issues:
        return tool_result(success=True, issues=[], message="✅ 质检通过，未发现问题")

    critical = [i for i in issues if i["level"] == "critical"]
    warnings = [i for i in issues if i["level"] == "warning"]
    info = [i for i in issues if i["level"] == "info"]

    lines = [f"质检结果（共 {len(issues)} 个问题）："]
    if critical:
        lines.append(f"\n🔴 严重（{len(critical)} 个）：")
        for i in critical:
            lines.append(f"  {i['icon']} [{i['voucher_id']}] {i['message']}")
    if warnings:
        lines.append(f"\n🟡 警告（{len(warnings)} 个）：")
        for i in warnings:
            lines.append(f"  {i['icon']} [{i['voucher_id']}] {i['message']}")
    if info:
        lines.append(f"\n🟢 提示（{len(info)} 个）：")
        for i in info:
            lines.append(f"  {i['icon']} {i['message']}")

    return tool_result(success=True, issues=issues,
                       critical=len(critical), warnings=len(warnings), info=len(info),
                       message="\n".join(lines))


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="check_vouchers",
    toolset="quality",
    schema={
        "name": "check_vouchers",
        "description": "质检——检查凭证和账务数据的合规性和风险。用户说'帮我检查一下'、'有没有问题'、'质检'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "period_id": {"type": "string", "description": "检查指定期间，如2026-05"},
            },
        },
    },
    handler=check_vouchers,
    emoji="🔍",
)
