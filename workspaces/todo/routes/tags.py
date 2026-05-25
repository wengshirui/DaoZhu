"""标签路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class TagCreate(BaseModel):
    name: str
    color: str = "#6366F1"


@router.get("/")
def list_tags():
    """获取所有标签"""
    db = get_db()
    tags = [dict(r) for r in db.execute("SELECT * FROM tags ORDER BY name").fetchall()]
    db.close()
    return {"tags": tags}


@router.post("/")
def create_tag(data: TagCreate):
    """创建标签"""
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO tags (name, color) VALUES (?, ?)", (data.name, data.color)
        )
        db.commit()
        tag = dict(db.execute("SELECT * FROM tags WHERE id = ?", (cursor.lastrowid,)).fetchone())
    except Exception:
        raise HTTPException(400, "标签已存在")
    finally:
        db.close()
    return tag


@router.delete("/{tag_id}")
def delete_tag(tag_id: int):
    """删除标签"""
    db = get_db()
    if not db.execute("SELECT 1 FROM tags WHERE id = ?", (tag_id,)).fetchone():
        raise HTTPException(404, "标签不存在")
    db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    db.commit()
    db.close()
    return {"success": True}


@router.post("/{task_id}/tags/{tag_id}")
def add_tag_to_task(task_id: int, tag_id: int):
    """给任务添加标签"""
    db = get_db()
    try:
        db.execute("INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)", (task_id, tag_id))
        db.commit()
    finally:
        db.close()
    return {"success": True}


@router.delete("/{task_id}/tags/{tag_id}")
def remove_tag_from_task(task_id: int, tag_id: int):
    """移除任务标签"""
    db = get_db()
    db.execute("DELETE FROM task_tags WHERE task_id = ? AND tag_id = ?", (task_id, tag_id))
    db.commit()
    db.close()
    return {"success": True}
