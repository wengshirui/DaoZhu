"""笔记 CRUD 路由"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class ItemCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "active"


class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@router.get("/")
def list_items(status: Optional[str] = None):
    """获取列表"""
    db = get_db()
    query = "SELECT * FROM notes"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    items = [dict(r) for r in db.execute(query, params).fetchall()]
    db.close()
    return {"items": items}


@router.get("/{item_id}")
def get_item(item_id: int):
    """获取单个"""
    db = get_db()
    item = db.execute("SELECT * FROM notes WHERE id = ?", (item_id,)).fetchone()
    db.close()
    if not item:
        raise HTTPException(404, "不存在")
    return dict(item)


@router.post("/")
def create_item(data: ItemCreate):
    """创建"""
    db = get_db()
    cursor = db.execute(
        "INSERT INTO notes (title, description, status) VALUES (?, ?, ?)",
        (data.title, data.description, data.status),
    )
    db.commit()
    item = dict(db.execute("SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)).fetchone())
    db.close()
    return item


@router.put("/{item_id}")
def update_item(item_id: int, data: ItemUpdate):
    """更新"""
    db = get_db()
    if not db.execute("SELECT 1 FROM notes WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "不存在")

    updates, params = [], []
    for field, value in data.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ?")
        params.append(value)
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(item_id)

    db.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    item = dict(db.execute("SELECT * FROM notes WHERE id = ?", (item_id,)).fetchone())
    db.close()
    return item


@router.delete("/{item_id}")
def delete_item(item_id: int):
    """删除"""
    db = get_db()
    if not db.execute("SELECT 1 FROM notes WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "不存在")
    db.execute("DELETE FROM notes WHERE id = ?", (item_id,))
    db.commit()
    db.close()
    return {"success": True}
