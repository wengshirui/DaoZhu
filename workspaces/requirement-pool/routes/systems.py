"""系统 CRUD 路由"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class SystemCreate(BaseModel):
    name: str
    description: str = ""
    sort_order: int = 0


class SystemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("/")
def list_systems():
    """获取所有系统列表（按排序顺序）"""
    db = get_db()
    rows = db.execute("SELECT * FROM systems ORDER BY sort_order ASC, id ASC").fetchall()
    systems = [dict(r) for r in rows]
    for s in systems:
        cnt = db.execute("SELECT COUNT(*) as c FROM requirements WHERE system_id = ?", (s["id"],)).fetchone()
        s["requirement_count"] = cnt["c"]
    db.close()
    return {"systems": systems}


@router.get("/{system_id}")
def get_system(system_id: int):
    """获取单个系统"""
    db = get_db()
    row = db.execute("SELECT * FROM systems WHERE id = ?", (system_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "系统不存在")
    return dict(row)


@router.post("/")
def create_system(data: SystemCreate):
    """创建系统"""
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO systems (name, description, sort_order) VALUES (?, ?, ?)",
            (data.name, data.description, data.sort_order),
        )
        db.commit()
        item = dict(db.execute("SELECT * FROM systems WHERE id = ?", (cursor.lastrowid,)).fetchone())
        db.close()
        return item
    except Exception as e:
        db.close()
        raise HTTPException(400, f"创建失败：{str(e)}")


@router.put("/{system_id}")
def update_system(system_id: int, data: SystemUpdate):
    """更新系统"""
    db = get_db()
    row = db.execute("SELECT 1 FROM systems WHERE id = ?", (system_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "系统不存在")

    updates, params = [], []
    for field, value in data.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ?")
        params.append(value)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(system_id)
        db.execute(f"UPDATE systems SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()

    item = dict(db.execute("SELECT * FROM systems WHERE id = ?", (system_id,)).fetchone())
    db.close()
    return item


@router.delete("/{system_id}")
def delete_system(system_id: int):
    """删除系统（会级联删除其下所有需求）"""
    db = get_db()
    row = db.execute("SELECT 1 FROM systems WHERE id = ?", (system_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "系统不存在")
    db.execute("DELETE FROM requirements WHERE system_id = ?", (system_id,))
    db.execute("DELETE FROM systems WHERE id = ?", (system_id,))
    db.commit()
    db.close()
    return {"success": True, "message": "系统及其下所有需求已删除"}
