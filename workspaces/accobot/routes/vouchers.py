"""凭证管理路由"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class EntryItem(BaseModel):
    account_code: str
    summary: str = ""
    debit: float = 0
    credit: float = 0


class VoucherCreate(BaseModel):
    company_id: str = "demo"
    voucher_date: str
    summary: str = ""
    entries: list[EntryItem] = []


@router.get("/")
def list_vouchers(
    company_id: str = "demo",
    status: Optional[str] = None,
    limit: int = 50,
):
    """获取凭证列表"""
    db = get_db()
    query = "SELECT * FROM vouchers WHERE company_id = ?"
    params: list = [company_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY voucher_date DESC, created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(query, params).fetchall()
    db.close()
    return {"vouchers": [dict(r) for r in rows]}


@router.get("/{voucher_id}")
def get_voucher(voucher_id: str):
    """获取凭证详情（含分录）"""
    db = get_db()
    voucher = db.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,)).fetchone()
    if not voucher:
        db.close()
        raise HTTPException(404, "凭证不存在")

    entries = db.execute(
        """SELECT e.*, a.name as account_name
           FROM entries e
           LEFT JOIN accounts a ON e.account_code = a.code
           WHERE e.voucher_id = ?
           ORDER BY e.id""",
        (voucher_id,),
    ).fetchall()
    db.close()

    result = dict(voucher)
    result["entries"] = [dict(e) for e in entries]
    return result


@router.post("/")
def create_voucher(data: VoucherCreate):
    """创建凭证（含分录）"""
    # 验证借贷平衡
    total_debit = sum(e.debit for e in data.entries)
    total_credit = sum(e.credit for e in data.entries)
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(400, f"借贷不平衡: 借方 {total_debit} ≠ 贷方 {total_credit}")

    if not data.entries:
        raise HTTPException(400, "凭证必须包含至少一条分录")

    voucher_id = str(uuid.uuid4())[:8]
    db = get_db()

    db.execute(
        """INSERT INTO vouchers (id, company_id, voucher_date, summary, status)
           VALUES (?, ?, ?, ?, 'draft')""",
        (voucher_id, data.company_id, data.voucher_date, data.summary),
    )

    for entry in data.entries:
        db.execute(
            """INSERT INTO entries (voucher_id, account_code, summary, debit, credit)
               VALUES (?, ?, ?, ?, ?)""",
            (voucher_id, entry.account_code, entry.summary, entry.debit, entry.credit),
        )

    db.commit()
    result = dict(db.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,)).fetchone())
    result["entries"] = [dict(r) for r in db.execute(
        "SELECT * FROM entries WHERE voucher_id = ?", (voucher_id,)
    ).fetchall()]
    db.close()
    return result


@router.put("/{voucher_id}/status")
def update_voucher_status(voucher_id: str, body: dict):
    """更新凭证状态（draft → posted → void）"""
    status = body.get("status")
    if status not in ("draft", "posted", "void"):
        raise HTTPException(400, "无效状态")

    db = get_db()
    if not db.execute("SELECT 1 FROM vouchers WHERE id = ?", (voucher_id,)).fetchone():
        db.close()
        raise HTTPException(404, "凭证不存在")

    db.execute(
        "UPDATE vouchers SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now().isoformat(), voucher_id),
    )
    db.commit()
    result = dict(db.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,)).fetchone())
    db.close()
    return result


@router.delete("/{voucher_id}")
def delete_voucher(voucher_id: str):
    """删除凭证（仅 draft 状态可删）"""
    db = get_db()
    voucher = db.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,)).fetchone()
    if not voucher:
        db.close()
        raise HTTPException(404, "凭证不存在")
    if voucher["status"] != "draft":
        db.close()
        raise HTTPException(400, "只能删除草稿状态的凭证")

    db.execute("DELETE FROM vouchers WHERE id = ?", (voucher_id,))
    db.commit()
    db.close()
    return {"success": True}
