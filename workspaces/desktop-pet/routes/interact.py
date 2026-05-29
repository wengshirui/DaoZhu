"""宠物互动 — 喂食、喂水、抚摸等"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db

router = APIRouter()


class InteractRequest(BaseModel):
    pet_id: int
    action: str  # feed / water / pet / play


# 互动效果映射
ACTIONS = {
    "feed": {"field": "hunger", "change": 30, "time_field": "last_fed_at"},
    "water": {"field": "thirst", "change": 35, "time_field": "last_watered_at"},
    "pet": {"field": "happiness", "change": 20, "time_field": "last_interact_at"},
    "play": {"field": "happiness", "change": 15, "time_field": "last_interact_at"},
}


@router.post("/")
async def interact(req: InteractRequest):
    """执行互动操作"""
    if req.action not in ACTIONS:
        raise HTTPException(400, f"未知操作: {req.action}，可选: {list(ACTIONS.keys())}")

    effect = ACTIONS[req.action]
    db = get_db()

    # 检查宠物存在
    pet = db.execute("SELECT id FROM pets WHERE id = ?", (req.pet_id,)).fetchone()
    if not pet:
        db.close()
        raise HTTPException(404, "宠物不存在")

    # 更新状态
    now = datetime.now().isoformat()
    field = effect["field"]
    change = effect["change"]

    db.execute(
        f"""UPDATE pet_state
            SET {field} = MIN(100, {field} + ?),
                {effect['time_field']} = ?,
                updated_at = ?
            WHERE pet_id = ?""",
        (change, now, now, req.pet_id),
    )

    # 记录互动
    db.execute(
        "INSERT INTO interactions (pet_id, action, value_change) VALUES (?, ?, ?)",
        (req.pet_id, req.action, change),
    )
    db.commit()

    # 返回更新后的状态
    state = db.execute(
        "SELECT hunger, thirst, happiness, energy FROM pet_state WHERE pet_id = ?",
        (req.pet_id,),
    ).fetchone()
    db.close()

    return {
        "success": True,
        "action": req.action,
        "effect": f"+{change} {field}",
        "state": dict(state) if state else None,
    }


@router.get("/history/{pet_id}")
async def get_history(pet_id: int, limit: int = 20):
    """获取互动历史"""
    db = get_db()
    rows = db.execute(
        """SELECT action, value_change, created_at
           FROM interactions WHERE pet_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (pet_id, limit),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]
