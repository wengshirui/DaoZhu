"""Todo / reminder routes — accounting, tax, business, social."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/todos")
async def get_todos():
    """Return todo/reminder items grouped by category."""
    from datetime import date
    from accobot.db.manager import DBManager

    today = date.today()
    mgr = DBManager.get_instance()
    accounting_todos = []
    tax_todos = []
    business_todos = []
    social_todos = []

    if mgr.accounting:
        # Draft vouchers
        draft_vouchers = mgr.accounting.list_vouchers(status="draft", limit=100)
        if draft_vouchers:
            accounting_todos.append({
                "title": f"{len(draft_vouchers)} 张凭证待审核",
                "due_date": "尽快处理",
                "overdue": False,
            })

        # Check if current period needs closing
        current_period = mgr.accounting.get_current_period()
        if current_period:
            period_month = current_period.get("month", 0)
            if today.month > period_month and today.day > 15:
                accounting_todos.append({
                    "title": f"{current_period['id']} 期间待结账",
                    "due_date": f"建议 {today.month}月15日前",
                    "overdue": today.day > 15,
                })

    # Tax reminders (simplified — based on calendar)
    if today.day <= 15:
        tax_todos.append({
            "title": "增值税申报",
            "due_date": f"{today.month}月15日",
            "overdue": False,
        })
    if today.day <= 15 and today.month in (1, 4, 7, 10):
        tax_todos.append({
            "title": "企业所得税季度预缴",
            "due_date": f"{today.month}月15日",
            "overdue": False,
        })

    return {
        "categories": [
            {"name": "会计", "icon": "📋", "items": accounting_todos},
            {"name": "税务", "icon": "🏛️", "items": tax_todos},
            {"name": "经营", "icon": "💼", "items": business_todos},
            {"name": "社保", "icon": "🏥", "items": social_todos},
        ],
        "total": len(accounting_todos) + len(tax_todos) + len(business_todos) + len(social_todos),
    }
