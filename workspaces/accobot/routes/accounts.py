"""会计科目路由"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class AccountCreate(BaseModel):
    code: str
    name: str
    category: str
    company_id: str = "demo"
    balance_direction: str = "debit"
    parent_code: Optional[str] = None


@router.get("/")
def list_accounts(
    company_id: str = "demo",
    category: Optional[str] = None,
):
    """获取科目列表"""
    db = get_db()
    query = "SELECT * FROM accounts WHERE company_id = ? AND is_active = 1"
    params = [company_id]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY code"
    rows = db.execute(query, params).fetchall()
    db.close()
    return {"accounts": [dict(r) for r in rows]}


@router.get("/search")
def search_accounts(q: str, company_id: str = "demo"):
    """搜索科目（按编码或名称）"""
    db = get_db()
    rows = db.execute(
        """SELECT * FROM accounts
           WHERE company_id = ? AND is_active = 1
             AND (code LIKE ? OR name LIKE ?)
           ORDER BY code LIMIT 20""",
        (company_id, f"%{q}%", f"%{q}%"),
    ).fetchall()
    db.close()
    return {"accounts": [dict(r) for r in rows]}


@router.post("/")
def create_account(data: AccountCreate):
    """创建科目"""
    db = get_db()
    try:
        db.execute(
            """INSERT INTO accounts (code, company_id, name, category, balance_direction, parent_code)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data.code, data.company_id, data.name, data.category,
             data.balance_direction, data.parent_code),
        )
        db.commit()
    except Exception:
        raise HTTPException(400, "科目编码已存在")
    row = db.execute("SELECT * FROM accounts WHERE code = ?", (data.code,)).fetchone()
    db.close()
    return dict(row)


@router.get("/{code}/balance")
def get_account_balance(code: str, company_id: str = "demo"):
    """获取科目余额"""
    db = get_db()
    # 计算借方合计和贷方合计
    row = db.execute(
        """SELECT COALESCE(SUM(e.debit), 0) as total_debit,
                  COALESCE(SUM(e.credit), 0) as total_credit
           FROM entries e
           JOIN vouchers v ON e.voucher_id = v.id
           WHERE e.account_code = ? AND v.company_id = ? AND v.status != 'void'""",
        (code, company_id),
    ).fetchone()
    db.close()

    total_debit = row["total_debit"]
    total_credit = row["total_credit"]
    balance = total_debit - total_credit

    return {
        "code": code,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balance": balance,
    }
