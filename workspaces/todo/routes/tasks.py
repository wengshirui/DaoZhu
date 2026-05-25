"""任务 CRUD 路由"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    project_id: Optional[int] = None
    due_date: Optional[date] = None
    sort_order: Optional[int] = None


@router.get("/")
def list_tasks(
    status: Optional[str] = None,
    project_id: Optional[int] = None,
    priority: Optional[str] = None,
    today: bool = False,
):
    """获取任务列表，支持筛选"""
    db = get_db()
    query = "SELECT * FROM tasks WHERE parent_id IS NULL"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if today:
        query += " AND (due_date = ? OR (due_date IS NULL AND status != 'done'))"
        params.append(date.today().isoformat())

    query += " ORDER BY sort_order, created_at DESC"
    tasks = [dict(r) for r in db.execute(query, params).fetchall()]

    # 附加子任务数量
    for task in tasks:
        count = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE parent_id = ?", (task["id"],)
        ).fetchone()[0]
        task["subtask_count"] = count
        done = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE parent_id = ? AND status = 'done'",
            (task["id"],),
        ).fetchone()[0]
        task["subtask_done"] = done

    db.close()
    return {"tasks": tasks}


@router.get("/{task_id}")
def get_task(task_id: int):
    """获取单个任务详情（含子任务）"""
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(404, "任务不存在")

    result = dict(task)
    subtasks = [
        dict(r)
        for r in db.execute(
            "SELECT * FROM tasks WHERE parent_id = ? ORDER BY sort_order",
            (task_id,),
        ).fetchall()
    ]
    result["subtasks"] = subtasks

    # 获取标签
    tags = [
        dict(r)
        for r in db.execute(
            "SELECT t.* FROM tags t JOIN task_tags tt ON t.id = tt.tag_id WHERE tt.task_id = ?",
            (task_id,),
        ).fetchall()
    ]
    result["tags"] = tags
    db.close()
    return result


@router.post("/")
def create_task(data: TaskCreate):
    """创建任务"""
    db = get_db()
    cursor = db.execute(
        """INSERT INTO tasks (title, description, priority, project_id, parent_id, due_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data.title, data.description, data.priority,
         data.project_id, data.parent_id,
         data.due_date.isoformat() if data.due_date else None),
    )
    db.commit()
    task = dict(db.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone())
    db.close()
    return task


@router.put("/{task_id}")
def update_task(task_id: int, data: TaskUpdate):
    """更新任务"""
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(404, "任务不存在")

    updates = []
    params = []
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "due_date" and value:
            value = value.isoformat()
        updates.append(f"{field} = ?")
        params.append(value)

    # 如果标记完成，记录完成时间
    if data.status == "done" and task["status"] != "done":
        updates.append("completed_at = ?")
        params.append(datetime.now().isoformat())
    elif data.status and data.status != "done":
        updates.append("completed_at = NULL")

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(task_id)

    db.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    result = dict(db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())
    db.close()
    return result


@router.delete("/{task_id}")
def delete_task(task_id: int):
    """删除任务（级联删除子任务）"""
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(404, "任务不存在")
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    db.close()
    return {"success": True}
