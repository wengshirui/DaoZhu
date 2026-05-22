"""Quality check & risk control tools.

Toolset: "quality"
Checks vouchers and operations for compliance risks.

Now delegates to quality_engine.py for per-voucher checks (REQ-021).
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

    # Use quality engine for per-voucher checks
    from accobot.tools.quality_engine import run_quality_check, save_quality_result

    all_issues = []

    for v in vouchers:
        result = run_quality_check(v["id"], db)
        save_quality_result(v["id"], result, db)

        for issue in result.issues:
            all_issues.append({
                "level": issue.level,
                "icon": {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(issue.level, "⚪"),
                "voucher_id": v["id"],
                "message": issue.message,
            })

    # Additional batch-level checks
    draft_count = sum(1 for v in vouchers if v["status"] == "draft")
    if draft_count > 10:
        all_issues.append({
            "level": "info",
            "icon": "🟢",
            "voucher_id": "",
            "message": f"有 {draft_count} 张凭证处于草稿状态，建议及时审核过账",
        })

    # Format output
    if not all_issues:
        return tool_result(success=True, issues=[], message="✅ 质检通过，未发现问题")

    critical = [i for i in all_issues if i["level"] == "critical"]
    warnings = [i for i in all_issues if i["level"] == "warning"]
    info = [i for i in all_issues if i["level"] == "info"]

    lines = [f"质检结果（共 {len(all_issues)} 个问题）："]
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

    return tool_result(success=True, issues=all_issues,
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
