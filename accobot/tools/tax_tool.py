"""Tax calculation tools — VAT, income tax, surcharges.

Toolset: "tax"
Calculate tax amounts based on accounting data and tax rules.
"""

from datetime import date
from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


def _get_company_info():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    cid = mgr.current_company_id
    if not cid:
        return None
    return mgr.master.get_company(cid)


def calculate_vat(args: dict, **kwargs) -> str:
    """Calculate VAT (增值税) based on revenue data."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    company = _get_company_info()
    taxpayer_type = company.get("taxpayer_type", "small_scale") if company else "small_scale"

    # Get revenue from income accounts
    income_accounts = db.list_accounts(category="income")
    total_revenue = 0.0
    for acct in income_accounts:
        if not acct["is_leaf"]:
            continue
        bal = db.get_account_balance(acct["code"])
        total_revenue += bal["balance"]

    if total_revenue == 0:
        return tool_result(success=True, vat=0, message="本期无收入，增值税为 0")

    # Calculate VAT
    if taxpayer_type == "small_scale":
        # 小规模纳税人：征收率 3%（2026年减按1%）
        rate = 0.01  # Current preferential rate
        tax_exclusive_revenue = total_revenue / (1 + rate)
        vat = tax_exclusive_revenue * rate
        rate_label = "1%（小规模优惠）"

        # Quarterly exemption check (季度30万免征)
        quarterly_exempt = total_revenue <= 300000
    else:
        # 一般纳税人：销项 - 进项
        rate = 0.13  # Default rate, simplified
        # Get output VAT (销项) from 应交增值税 account
        vat_account = db.get_account("222101")
        if vat_account:
            bal = db.get_account_balance("222101")
            vat = bal["balance"]  # Credit balance = tax payable
        else:
            tax_exclusive_revenue = total_revenue / (1 + rate)
            vat = tax_exclusive_revenue * rate
        rate_label = "13%（一般纳税人）"
        quarterly_exempt = False

    lines = [f"增值税计算："]
    lines.append(f"  纳税人类型：{'小规模' if taxpayer_type == 'small_scale' else '一般纳税人'}")
    lines.append(f"  本期收入：{total_revenue:,.2f}")
    lines.append(f"  适用税率：{rate_label}")
    lines.append(f"  应纳增值税：{vat:,.2f}")

    if quarterly_exempt:
        lines.append(f"  💡 季度收入未超30万，可享受免征增值税优惠")
        vat = 0

    return tool_result(success=True, vat=round(vat, 2), revenue=total_revenue,
                       taxpayer_type=taxpayer_type, exempt=quarterly_exempt,
                       message="\n".join(lines))


def calculate_surcharges(args: dict, **kwargs) -> str:
    """Calculate surcharges (附加税) based on VAT amount."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    vat_amount = args.get("vat_amount")

    if vat_amount is None:
        # Auto-calculate from VAT
        from accobot.tools.tax_tool import calculate_vat
        import json
        vat_result = json.loads(calculate_vat({}))
        if "error" in vat_result:
            return tool_error(vat_result["error"])
        vat_amount = vat_result.get("vat", 0)

    vat_amount = float(vat_amount)

    if vat_amount == 0:
        return tool_result(success=True, total=0, message="增值税为0，附加税也为0")

    # Standard surcharge rates
    city_tax = vat_amount * 0.07       # 城建税 7%（市区）
    edu_surcharge = vat_amount * 0.03  # 教育费附加 3%
    local_edu = vat_amount * 0.02      # 地方教育附加 2%
    total = city_tax + edu_surcharge + local_edu

    # Small-scale taxpayer 50% reduction (六税两费减半)
    company = _get_company_info()
    is_small = company and company.get("taxpayer_type") == "small_scale"
    if is_small:
        city_tax *= 0.5
        edu_surcharge *= 0.5
        local_edu *= 0.5
        total = city_tax + edu_surcharge + local_edu

    lines = [f"附加税计算（基于增值税 {vat_amount:,.2f}）："]
    lines.append(f"  城市维护建设税（7%）：{city_tax:,.2f}")
    lines.append(f"  教育费附加（3%）：    {edu_surcharge:,.2f}")
    lines.append(f"  地方教育附加（2%）：  {local_edu:,.2f}")
    if is_small:
        lines.append(f"  💡 小规模纳税人享受六税两费减半")
    lines.append(f"  ─────────────────")
    lines.append(f"  附加税合计：          {total:,.2f}")

    return tool_result(success=True, city_tax=round(city_tax, 2),
                       edu_surcharge=round(edu_surcharge, 2),
                       local_edu=round(local_edu, 2),
                       total=round(total, 2), message="\n".join(lines))


def tax_calendar(args: dict, **kwargs) -> str:
    """Show upcoming tax filing deadlines."""
    today = date.today()
    month = today.month
    year = today.year

    deadlines = []

    # Monthly deadlines (by 15th)
    if today.day <= 15:
        deadlines.append({"tax": "增值税", "deadline": f"{year}-{month:02d}-15", "period": "月度"})
        deadlines.append({"tax": "个人所得税", "deadline": f"{year}-{month:02d}-15", "period": "月度"})
        deadlines.append({"tax": "附加税", "deadline": f"{year}-{month:02d}-15", "period": "月度"})

    # Quarterly (months 1,4,7,10)
    if month in (1, 4, 7, 10) and today.day <= 15:
        deadlines.append({"tax": "企业所得税（季度预缴）", "deadline": f"{year}-{month:02d}-15", "period": "季度"})

    # Annual
    if month <= 5:
        deadlines.append({"tax": "企业所得税（汇算清缴）", "deadline": f"{year}-05-31", "period": "年度"})
    if month <= 6:
        deadlines.append({"tax": "工商年报", "deadline": f"{year}-06-30", "period": "年度"})

    if not deadlines:
        return tool_result(success=True, deadlines=[], message="本月申报期已过，下个申报期在下月1-15日")

    lines = [f"📅 税务日历（{year}年{month}月）："]
    for d in deadlines:
        days_left = (date.fromisoformat(d["deadline"]) - today).days
        status = f"还剩 {days_left} 天" if days_left > 0 else "⚠️ 今天截止！" if days_left == 0 else "❌ 已过期"
        lines.append(f"  {d['tax']:<20} 截止：{d['deadline']}  {status}")

    return tool_result(success=True, deadlines=deadlines, message="\n".join(lines))


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="calculate_vat",
    toolset="tax",
    schema={
        "name": "calculate_vat",
        "description": "计算增值税。用户问'要交多少增值税'、'增值税是多少'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=calculate_vat,
    emoji="🧾",
)

registry.register(
    name="calculate_surcharges",
    toolset="tax",
    schema={
        "name": "calculate_surcharges",
        "description": "计算附加税（城建税+教育费附加+地方教育附加）。用户问'附加税多少'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "vat_amount": {"type": "number", "description": "增值税金额（不填则自动计算）"},
            },
        },
    },
    handler=calculate_surcharges,
    emoji="🧾",
)

registry.register(
    name="tax_calendar",
    toolset="tax",
    schema={
        "name": "tax_calendar",
        "description": "查看报税日历——近期的申报截止日期。用户问'什么时候报税'、'申报截止日期'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=tax_calendar,
    emoji="📅",
)
