"""Configuration management tools — accounts, auxiliary items, periods.

Toolset: "config"
Lets the AI agent manage chart of accounts, auxiliary accounting items,
and accounting periods through natural language conversation.
"""

import json
from accobot.tools.registry import registry, tool_result, tool_error


def _get_db():
    """Get the current accounting database."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return None
    return mgr.accounting


# =========================================================================
# 科目管理工具
# =========================================================================

def list_accounts(args: dict, **kwargs) -> str:
    """List accounts, optionally filtered by category or keyword."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    category = args.get("category")
    keyword = args.get("keyword")

    if keyword:
        accounts = db.search_accounts(keyword)
    else:
        accounts = db.list_accounts(category=category)

    if not accounts:
        msg = "未找到匹配的科目"
        if keyword:
            msg += f"（关键词：{keyword}）"
        return tool_result(success=True, accounts=[], message=msg)

    return tool_result(
        success=True,
        accounts=[{"code": a["code"], "name": a["name"], "category": a["category"]} for a in accounts],
        count=len(accounts),
        message=f"找到 {len(accounts)} 个科目",
    )


def add_account(args: dict, **kwargs) -> str:
    """Add a new account to the chart of accounts."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    code = args.get("code", "").strip()
    name = args.get("name", "").strip()
    category = args.get("category", "").strip()
    balance_direction = args.get("balance_direction", "debit")
    parent_code = args.get("parent_code")

    if not code:
        return tool_error("科目编码不能为空")
    if not name:
        return tool_error("科目名称不能为空")
    if category not in ("asset", "liability", "equity", "cost", "income", "expense"):
        return tool_error("科目类别必须是：asset/liability/equity/cost/income/expense")

    existing = db.get_account(code)
    if existing:
        return tool_error(f"科目编码 {code} 已存在（{existing['name']}）")

    result = db.add_account(
        code=code, name=name, category=category,
        balance_direction=balance_direction, parent_code=parent_code,
    )
    return tool_result(success=True, account=result, message=f"已添加科目：{code} {name}")


def update_account(args: dict, **kwargs) -> str:
    """Update an existing account."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    code = args.get("code", "").strip()
    if not code:
        return tool_error("请指定要修改的科目编码")

    existing = db.get_account(code)
    if not existing:
        return tool_error(f"科目 {code} 不存在")

    name = args.get("name", existing["name"])
    is_active = args.get("is_active", existing["is_active"])
    aux_attributes = args.get("aux_attributes", existing["aux_attributes"])

    db.add_account(
        code=code, name=name, category=existing["category"],
        balance_direction=existing["balance_direction"],
        parent_code=existing["parent_code"],
        is_leaf=bool(existing["is_leaf"]),
        aux_attributes=aux_attributes if isinstance(aux_attributes, str) else json.dumps(aux_attributes),
    )
    return tool_result(success=True, message=f"已更新科目：{code} {name}")


# =========================================================================
# 辅助核算管理工具
# =========================================================================

def list_aux_items(args: dict, **kwargs) -> str:
    """List auxiliary accounting items by type."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    item_type = args.get("type", "")
    valid_types = ("department", "customer", "supplier", "project", "employee")

    if item_type and item_type not in valid_types:
        return tool_error(f"辅助核算类型必须是：{'/'.join(valid_types)}")

    # Query from database
    with db._lock:
        sql = "SELECT * FROM aux_items WHERE is_active = 1"
        params = []
        if item_type:
            sql += " AND type = ?"
            params.append(item_type)
        sql += " ORDER BY type, code"
        cur = db._conn.execute(sql, params)
        items = [dict(row) for row in cur.fetchall()]

    type_names = {
        "department": "部门", "customer": "客户", "supplier": "供应商",
        "project": "项目", "employee": "员工",
    }
    type_label = type_names.get(item_type, "全部")

    return tool_result(
        success=True,
        items=[{"id": i["id"], "type": i["type"], "code": i.get("code", ""), "name": i["name"]} for i in items],
        count=len(items),
        message=f"{type_label}辅助核算项目共 {len(items)} 个",
    )


def add_aux_item(args: dict, **kwargs) -> str:
    """Add a new auxiliary accounting item."""
    import uuid
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    item_type = args.get("type", "").strip()
    name = args.get("name", "").strip()
    code = args.get("code", "").strip()

    valid_types = ("department", "customer", "supplier", "project", "employee")
    if item_type not in valid_types:
        return tool_error(f"辅助核算类型必须是：{'/'.join(valid_types)}")
    if not name:
        return tool_error("名称不能为空")

    item_id = uuid.uuid4().hex[:8]
    with db._lock:
        db._conn.execute(
            "INSERT INTO aux_items (id, type, code, name) VALUES (?, ?, ?, ?)",
            (item_id, item_type, code, name),
        )

    type_names = {"department": "部门", "customer": "客户", "supplier": "供应商", "project": "项目", "employee": "员工"}
    return tool_result(success=True, item={"id": item_id, "type": item_type, "name": name}, message=f"已添加{type_names[item_type]}：{name}")


# =========================================================================
# 会计期间管理工具
# =========================================================================

def list_periods(args: dict, **kwargs) -> str:
    """List accounting periods."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    periods = db.list_periods()
    return tool_result(
        success=True,
        periods=[{"id": p["id"], "year": p["year"], "month": p["month"], "status": p["status"]} for p in periods],
        count=len(periods),
        message=f"共 {len(periods)} 个会计期间",
    )


def close_period(args: dict, **kwargs) -> str:
    """Close an accounting period."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    period_id = args.get("period_id", "").strip()
    if not period_id:
        return tool_error("请指定要关闭的期间（如：2026-05）")

    with db._lock:
        cur = db._conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
        period = cur.fetchone()
        if not period:
            return tool_error(f"期间 {period_id} 不存在")
        if period["status"] == "closed":
            return tool_error(f"期间 {period_id} 已经是关闭状态")
        db._conn.execute("UPDATE periods SET status = 'closed' WHERE id = ?", (period_id,))

    return tool_result(success=True, message=f"已关闭期间：{period_id}")


def open_period(args: dict, **kwargs) -> str:
    """Reopen a closed accounting period."""
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    period_id = args.get("period_id", "").strip()
    if not period_id:
        return tool_error("请指定要重新开启的期间（如：2026-05）")

    with db._lock:
        cur = db._conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
        period = cur.fetchone()
        if not period:
            return tool_error(f"期间 {period_id} 不存在")
        if period["status"] == "open":
            return tool_error(f"期间 {period_id} 已经是开启状态")
        db._conn.execute("UPDATE periods SET status = 'open' WHERE id = ?", (period_id,))

    return tool_result(success=True, message=f"已重新开启期间：{period_id}")


def generate_periods(args: dict, **kwargs) -> str:
    """Generate 12 monthly periods for a year."""
    from accobot.db.templates import init_periods
    db = _get_db()
    if not db:
        return tool_error("请先选择或创建一个账套")

    year = args.get("year")
    if not year:
        from datetime import date
        year = date.today().year

    count = init_periods(db, int(year))
    return tool_result(success=True, count=count, message=f"已生成 {year} 年 {count} 个会计期间")


# =========================================================================
# Tool Registration
# =========================================================================

registry.register(
    name="list_accounts",
    toolset="config",
    schema={
        "name": "list_accounts",
        "description": "查询会计科目列表。可按类别筛选或按关键词搜索。用户问'有哪些费用科目'、'查一下银行相关的科目'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "科目类别筛选：asset/liability/equity/cost/income/expense"},
                "keyword": {"type": "string", "description": "搜索关键词（匹配科目名称或编码）"},
            },
        },
    },
    handler=list_accounts,
    emoji="📋",
)

registry.register(
    name="add_account",
    toolset="config",
    schema={
        "name": "add_account",
        "description": "新增一个会计科目。用户说'加一个科目'、'新建XX费用科目'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "科目编码（如560211）"},
                "name": {"type": "string", "description": "科目名称（如：快递费）"},
                "category": {"type": "string", "description": "类别：asset/liability/equity/cost/income/expense"},
                "balance_direction": {"type": "string", "description": "余额方向：debit（借方）或 credit（贷方）"},
                "parent_code": {"type": "string", "description": "上级科目编码（如：5602）"},
            },
            "required": ["code", "name", "category"],
        },
    },
    handler=add_account,
    emoji="➕",
)

registry.register(
    name="update_account",
    toolset="config",
    schema={
        "name": "update_account",
        "description": "修改会计科目的名称或辅助核算属性。用户说'把XX科目改名'、'给XX科目挂上部门核算'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "要修改的科目编码"},
                "name": {"type": "string", "description": "新的科目名称"},
                "aux_attributes": {"type": "array", "items": {"type": "string"}, "description": "辅助核算属性列表，如：['department', 'employee']"},
                "is_active": {"type": "boolean", "description": "是否启用"},
            },
            "required": ["code"],
        },
    },
    handler=update_account,
    emoji="✏️",
)

registry.register(
    name="list_aux_items",
    toolset="config",
    schema={
        "name": "list_aux_items",
        "description": "查询辅助核算项目列表（部门、客户、供应商、项目、员工）。用户问'有哪些部门'、'客户列表'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "类型：department/customer/supplier/project/employee"},
            },
        },
    },
    handler=list_aux_items,
    emoji="🏷️",
)

registry.register(
    name="add_aux_item",
    toolset="config",
    schema={
        "name": "add_aux_item",
        "description": "新增辅助核算项目。用户说'添加一个部门'、'新增客户XX公司'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "类型：department/customer/supplier/project/employee"},
                "name": {"type": "string", "description": "名称"},
                "code": {"type": "string", "description": "编码（可选）"},
            },
            "required": ["type", "name"],
        },
    },
    handler=add_aux_item,
    emoji="➕",
)

registry.register(
    name="list_periods",
    toolset="config",
    schema={
        "name": "list_periods",
        "description": "查询会计期间列表及状态。用户问'会计期间'、'哪些月份还开着'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=list_periods,
    emoji="📅",
)

registry.register(
    name="close_period",
    toolset="config",
    schema={
        "name": "close_period",
        "description": "关闭一个会计期间（关闭后该月不能再录入凭证）。用户说'结账'、'关闭X月'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "period_id": {"type": "string", "description": "期间ID，格式如：2026-05"},
            },
            "required": ["period_id"],
        },
    },
    handler=close_period,
    emoji="🔒",
)

registry.register(
    name="open_period",
    toolset="config",
    schema={
        "name": "open_period",
        "description": "重新开启一个已关闭的会计期间。用户说'反结账'、'重新打开X月'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "period_id": {"type": "string", "description": "期间ID，格式如：2026-05"},
            },
            "required": ["period_id"],
        },
    },
    handler=open_period,
    emoji="🔓",
)

registry.register(
    name="generate_periods",
    toolset="config",
    schema={
        "name": "generate_periods",
        "description": "为指定年份生成12个月的会计期间。用户说'生成2027年的期间'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "年份，如2027"},
            },
        },
    },
    handler=generate_periods,
    emoji="📅",
)
