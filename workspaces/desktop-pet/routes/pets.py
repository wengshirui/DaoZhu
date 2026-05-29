"""我的宠物 — CRUD 和状态管理"""

import json
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException

from db import get_db

router = APIRouter()

PETS_DIR = Path(__file__).parent.parent / "pets"


@router.get("/")
async def list_pets():
    """列出所有已下载的宠物"""
    db = get_db()
    rows = db.execute(
        """SELECT p.*, ps.hunger, ps.thirst, ps.happiness, ps.energy,
                  ps.last_fed_at, ps.last_watered_at, ps.updated_at as state_updated
           FROM pets p LEFT JOIN pet_state ps ON p.id = ps.pet_id
           ORDER BY p.is_active DESC, p.created_at DESC"""
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/active")
async def get_active_pet():
    """获取当前活跃宠物"""
    db = get_db()
    row = db.execute(
        """SELECT p.*, ps.hunger, ps.thirst, ps.happiness, ps.energy,
                  ps.last_fed_at, ps.last_watered_at
           FROM pets p LEFT JOIN pet_state ps ON p.id = ps.pet_id
           WHERE p.is_active = 1"""
    ).fetchone()
    db.close()
    if not row:
        return None
    pet = dict(row)
    # 计算状态衰减
    pet = _apply_decay(pet)
    return pet


@router.post("/{pet_id}/activate")
async def activate_pet(pet_id: int):
    """设置活跃宠物"""
    db = get_db()
    db.execute("UPDATE pets SET is_active = 0")
    result = db.execute(
        "UPDATE pets SET is_active = 1 WHERE id = ?", (pet_id,)
    )
    if result.rowcount == 0:
        db.close()
        raise HTTPException(404, "宠物不存在")
    db.commit()
    db.close()
    return {"success": True}


@router.delete("/{pet_id}")
async def delete_pet(pet_id: int):
    """删除宠物"""
    db = get_db()
    row = db.execute("SELECT name, local_path FROM pets WHERE id = ?", (pet_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "宠物不存在")

    # 删除文件
    import shutil
    pet_path = Path(row["local_path"])
    if pet_path.exists():
        shutil.rmtree(pet_path, ignore_errors=True)

    # 删除数据库记录（CASCADE 会删除 pet_state 和 interactions）
    db.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    db.commit()
    db.close()
    return {"success": True}


@router.get("/{pet_id}/state")
async def get_pet_state(pet_id: int):
    """获取宠物状态（含衰减计算）"""
    db = get_db()
    row = db.execute(
        """SELECT p.name, ps.* FROM pet_state ps
           JOIN pets p ON p.id = ps.pet_id
           WHERE ps.pet_id = ?""",
        (pet_id,),
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "宠物不存在")
    state = dict(row)
    return _apply_decay(state)


@router.get("/{pet_id}/spritesheet")
async def get_spritesheet_info(pet_id: int):
    """获取宠物 spritesheet 信息"""
    db = get_db()
    row = db.execute(
        "SELECT name, local_path, frame_width, frame_height, columns, rows FROM pets WHERE id = ?",
        (pet_id,),
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "宠物不存在")

    pet = dict(row)
    pet_dir = Path(pet["local_path"])
    pet_json_path = pet_dir / "pet.json"

    # 读取 pet.json 获取 spritesheet 文件名
    sheet_name = "spritesheet.webp"
    if pet_json_path.exists():
        try:
            meta = json.loads(pet_json_path.read_text(encoding="utf-8"))
            sheet_name = meta.get("spritesheet", sheet_name)
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "name": pet["name"],
        "spritesheet_url": f"/pets/{pet['name']}/{sheet_name}",
        "frame_width": pet["frame_width"],
        "frame_height": pet["frame_height"],
        "columns": pet["columns"],
        "rows": pet["rows"],
    }


def _apply_decay(state: dict) -> dict:
    """根据时间计算状态衰减"""
    updated = state.get("state_updated") or state.get("updated_at")
    if not updated:
        return state

    # 简单衰减：每小时 hunger -5, thirst -8, happiness -3, energy -2
    try:
        from datetime import datetime
        if isinstance(updated, str):
            last = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        else:
            last = updated
        now = datetime.now()
        hours = (now - last.replace(tzinfo=None)).total_seconds() / 3600

        if hours > 0:
            state["hunger"] = max(0, (state.get("hunger") or 100) - int(hours * 5))
            state["thirst"] = max(0, (state.get("thirst") or 100) - int(hours * 8))
            state["happiness"] = max(0, (state.get("happiness") or 100) - int(hours * 3))
            state["energy"] = max(0, (state.get("energy") or 100) - int(hours * 2))
    except (ValueError, TypeError):
        pass

    return state
