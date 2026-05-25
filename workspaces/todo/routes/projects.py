"""项目/分类路由"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    icon: str = "📁"
    color: str = "#2d9b83"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("/")
def list_projects():
    """获取所有项目（含任务统计）"""
    db = get_db()
    projects = [dict(r) for r in db.execute(
        "SELECT * FROM projects ORDER BY sort_order, id"
    ).fetchall()]

    for p in projects:
        total = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (p["id"],)
        ).fetchone()[0]
        done = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status = 'done'",
            (p["id"],),
        ).fetchone()[0]
        p["task_count"] = total
        p["done_count"] = done

    db.close()
    return {"projects": projects}


@router.post("/")
def create_project(data: ProjectCreate):
    """创建项目"""
    db = get_db()
    cursor = db.execute(
        "INSERT INTO projects (name, icon, color) VALUES (?, ?, ?)",
        (data.name, data.icon, data.color),
    )
    db.commit()
    project = dict(db.execute("SELECT * FROM projects WHERE id = ?", (cursor.lastrowid,)).fetchone())
    db.close()
    return project


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate):
    """更新项目"""
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        raise HTTPException(404, "项目不存在")

    updates = []
    params = []
    for field, value in data.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ?")
        params.append(value)

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(project_id)

    db.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    result = dict(db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    db.close()
    return result


@router.delete("/{project_id}")
def delete_project(project_id: int):
    """删除项目（任务的 project_id 置空）"""
    db = get_db()
    if not db.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone():
        raise HTTPException(404, "项目不存在")
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    db.close()
    return {"success": True}
