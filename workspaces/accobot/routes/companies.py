"""公司/账套管理路由"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class CompanyCreate(BaseModel):
    id: str
    name: str
    industry: str = ""
    taxpayer_type: str = "small_scale"
    accounting_standard: str = "small_enterprise"


@router.get("/")
def list_companies():
    """获取所有公司"""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM companies WHERE status = 'active' ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return {"companies": [dict(r) for r in rows]}


@router.get("/{company_id}")
def get_company(company_id: str):
    """获取单个公司"""
    db = get_db()
    row = db.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "公司不存在")
    return dict(row)


@router.post("/")
def create_company(data: CompanyCreate):
    """创建公司"""
    db = get_db()
    try:
        db.execute(
            """INSERT INTO companies (id, name, industry, taxpayer_type, accounting_standard)
               VALUES (?, ?, ?, ?, ?)""",
            (data.id, data.name, data.industry, data.taxpayer_type, data.accounting_standard),
        )
        db.commit()
    except Exception:
        raise HTTPException(400, "公司 ID 已存在")
    row = db.execute("SELECT * FROM companies WHERE id = ?", (data.id,)).fetchone()
    db.close()
    return dict(row)


@router.delete("/{company_id}")
def delete_company(company_id: str):
    """删除公司（软删除）"""
    db = get_db()
    db.execute("UPDATE companies SET status = 'archived' WHERE id = ?", (company_id,))
    db.commit()
    db.close()
    return {"success": True}
