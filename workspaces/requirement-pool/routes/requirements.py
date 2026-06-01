"""需求 CRUD 路由 — 支持分页 + 多条件筛选"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class RequirementCreate(BaseModel):
    system_id: int
    port: str = "web"
    module: str = ""
    name: str
    description: str = ""
    source: str = "产品"
    priority: int = 2
    proposer: str = ""
    propose_date: str = ""
    plan_date: str = ""
    status: str = "进入需求池"
    plan_version: str = ""
    actual_version: str = ""
    online_date: str = ""
    remark: str = ""


class RequirementUpdate(BaseModel):
    system_id: Optional[int] = None
    port: Optional[str] = None
    module: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    priority: Optional[int] = None
    proposer: Optional[str] = None
    propose_date: Optional[str] = None
    plan_date: Optional[str] = None
    status: Optional[str] = None
    plan_version: Optional[str] = None
    actual_version: Optional[str] = None
    online_date: Optional[str] = None
    remark: Optional[str] = None


@router.get("/")
def list_requirements(
    system_id: Optional[int] = Query(None, description="按系统筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    source: Optional[str] = Query(None, description="按来源筛选"),
    priority: Optional[int] = Query(None, description="按优先级筛选"),
    port: Optional[str] = Query(None, description="按端口筛选"),
    keyword: Optional[str] = Query(None, description="按名称/描述关键词搜索"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
):
    """获取需求列表（分页 + 多条件筛选 + 排序）"""
    db = get_db()

    conditions = []
    params = []

    if system_id is not None:
        conditions.append("r.system_id = ?")
        params.append(system_id)
    if status:
        conditions.append("r.status = ?")
        params.append(status)
    if source:
        conditions.append("r.source = ?")
        params.append(source)
    if priority is not None:
        conditions.append("r.priority = ?")
        params.append(priority)
    if port:
        conditions.append("r.port = ?")
        params.append(port)
    if keyword:
        conditions.append("(r.name LIKE ? OR r.description LIKE ?)")
        kw = f"%{keyword}%"
        params.append(kw)
        params.append(kw)

    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # 验证排序字段和方向
    valid_sort_fields = ["created_at", "plan_date", "propose_date", "priority"]
    if sort_by not in valid_sort_fields:
        sort_by = "created_at"
    
    sort_order = sort_order.lower()
    if sort_order not in ["asc", "desc"]:
        sort_order = "desc"

    # 处理 plan_date 为空的情况，空值排最后（SQLite兼容写法）
    if sort_by == "plan_date":
        if sort_order == "desc":
            order_clause = "ORDER BY r.plan_date IS NULL, r.plan_date DESC"
        else:
            order_clause = "ORDER BY r.plan_date IS NOT NULL, r.plan_date ASC"
    else:
        order_clause = f"ORDER BY r.{sort_by} {sort_order}"

    # 查总数
    count_sql = f"SELECT COUNT(*) as total FROM requirements r{where_clause}"
    total = db.execute(count_sql, params).fetchone()["total"]

    # 查分页数据
    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT r.*, s.name as system_name 
        FROM requirements r 
        LEFT JOIN systems s ON r.system_id = s.id
        {where_clause} 
        {order_clause}
        LIMIT ? OFFSET ?
    """
    rows = db.execute(data_sql, params + [page_size, offset]).fetchall()
    items = [dict(r) for r in rows]

    db.close()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


@router.get("/stats")
def get_stats():
    """获取统计信息"""
    db = get_db()
    total_reqs = db.execute("SELECT COUNT(*) as c FROM requirements").fetchone()["c"]
    total_systems = db.execute("SELECT COUNT(*) as c FROM systems").fetchone()["c"]

    status_dist = {}
    for r in db.execute("SELECT status, COUNT(*) as c FROM requirements GROUP BY status").fetchall():
        status_dist[r["status"]] = r["c"]

    db.close()
    return {
        "total_requirements": total_reqs,
        "total_systems": total_systems,
        "status_distribution": status_dist,
    }


@router.get("/{req_id}")
def get_requirement(req_id: int):
    """获取单个需求"""
    db = get_db()
    row = db.execute(
        "SELECT r.*, s.name as system_name FROM requirements r LEFT JOIN systems s ON r.system_id = s.id WHERE r.id = ?",
        (req_id,),
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "需求不存在")
    return dict(row)


@router.post("/")
def create_requirement(data: RequirementCreate):
    """创建需求"""
    db = get_db()
    # 验证系统存在
    if not db.execute("SELECT 1 FROM systems WHERE id = ?", (data.system_id,)).fetchone():
        db.close()
        raise HTTPException(400, "所选系统不存在")

    cursor = db.execute(
        """INSERT INTO requirements 
        (system_id, port, module, name, description, source, priority, proposer, 
         propose_date, plan_date, status, plan_version, actual_version, online_date, remark)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.system_id, data.port, data.module, data.name, data.description,
            data.source, data.priority, data.proposer, data.propose_date,
            data.plan_date, data.status, data.plan_version, data.actual_version,
            data.online_date, data.remark,
        ),
    )
    db.commit()
    item = dict(
        db.execute(
            "SELECT r.*, s.name as system_name FROM requirements r LEFT JOIN systems s ON r.system_id = s.id WHERE r.id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    )
    db.close()
    return item


@router.put("/{req_id}")
def update_requirement(req_id: int, data: RequirementUpdate):
    """更新需求"""
    db = get_db()
    row = db.execute("SELECT 1 FROM requirements WHERE id = ?", (req_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "需求不存在")

    # 如果更新 system_id，验证系统存在
    if data.system_id is not None and not db.execute("SELECT 1 FROM systems WHERE id = ?", (data.system_id,)).fetchone():
        db.close()
        raise HTTPException(400, "所选系统不存在")

    updates, params = [], []
    for field, value in data.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ?")
        params.append(value)

    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(req_id)
        db.execute(f"UPDATE requirements SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()

    item = dict(
        db.execute(
            "SELECT r.*, s.name as system_name FROM requirements r LEFT JOIN systems s ON r.system_id = s.id WHERE r.id = ?",
            (req_id,),
        ).fetchone()
    )
    db.close()
    return item


@router.delete("/{req_id}")
def delete_requirement(req_id: int):
    """删除需求"""
    db = get_db()
    if not db.execute("SELECT 1 FROM requirements WHERE id = ?", (req_id,)).fetchone():
        db.close()
        raise HTTPException(404, "需求不存在")
    db.execute("DELETE FROM requirements WHERE id = ?", (req_id,))
    db.commit()
    db.close()
    return {"success": True}
