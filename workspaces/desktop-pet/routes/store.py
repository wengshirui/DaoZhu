"""宠物商店 — 对接 Petdex manifest API + 本地下载"""

import json
import httpx
from pathlib import Path
from fastapi import APIRouter, HTTPException

from db import get_db

router = APIRouter()

PETS_DIR = Path(__file__).parent.parent / "pets"

# Petdex 公开 API（2700+ 宠物，含 spritesheet 直链）
PETDEX_MANIFEST = "https://petdex.crafter.run/api/manifest"
MANIFEST_CACHE = Path(__file__).parent.parent / "pets" / "_manifest.json"


@router.get("/manifest")
async def get_manifest(page: int = 1, per_page: int = 24, kind: str = ""):
    """获取宠物目录（从 Petdex manifest）"""
    manifest = _load_manifest()
    pets = manifest.get("pets", [])
    if kind:
        pets = [p for p in pets if p.get("kind", "").lower() == kind.lower()]
    total = len(pets)
    start = (page - 1) * per_page
    items = pets[start:start + per_page]
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": items,
    }


@router.get("/kinds")
async def get_kinds():
    """获取所有宠物类型"""
    manifest = _load_manifest()
    pets = manifest.get("pets", [])
    kind_count = {}
    for p in pets:
        k = p.get("kind", "unknown")
        kind_count[k] = kind_count.get(k, 0) + 1
    return sorted(kind_count.items(), key=lambda x: -x[1])


@router.post("/refresh")
async def refresh_manifest():
    """从 Petdex API 刷新宠物目录"""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(PETDEX_MANIFEST)
            if resp.status_code == 200:
                data = resp.json()
                MANIFEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
                MANIFEST_CACHE.write_text(
                    json.dumps(data, ensure_ascii=False),
                    encoding="utf-8",
                )
                return {"success": True, "total": data.get("total", 0)}
    except Exception as e:
        return {"success": False, "message": str(e)}
    return {"success": False, "message": "请求失败"}


@router.post("/download")
async def download_pet(slug: str):
    """从 Petdex 下载宠物到本地"""
    pet_dir = PETS_DIR / slug
    if pet_dir.exists() and (pet_dir / "spritesheet.webp").exists():
        raise HTTPException(400, f"宠物 '{slug}' 已存在本地")

    # 从 manifest 中找到该宠物
    manifest = _load_manifest()
    pets = manifest.get("pets", [])
    pet_info = next((p for p in pets if p["slug"] == slug), None)

    if not pet_info:
        raise HTTPException(404, f"宠物 '{slug}' 不在目录中，请先刷新目录")

    pet_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            # 下载 spritesheet
            sheet_url = pet_info.get("spritesheetUrl", "")
            if not sheet_url:
                raise HTTPException(404, "该宠物没有 spritesheet 资源")

            resp = await client.get(sheet_url)
            if resp.status_code != 200:
                raise HTTPException(502, f"spritesheet 下载失败 (HTTP {resp.status_code})")
            (pet_dir / "spritesheet.webp").write_bytes(resp.content)

            # 下载 pet.json（如果有）
            json_url = pet_info.get("petJsonUrl", "")
            if json_url:
                resp2 = await client.get(json_url)
                if resp2.status_code == 200:
                    (pet_dir / "pet.json").write_bytes(resp2.content)

            # 如果没有 pet.json，自己生成一个
            if not (pet_dir / "pet.json").exists():
                meta = {
                    "name": pet_info.get("displayName", slug),
                    "slug": slug,
                    "kind": pet_info.get("kind", ""),
                    "submittedBy": pet_info.get("submittedBy", ""),
                    "spritesheet": "spritesheet.webp",
                    "columns": 9,
                    "rows": 8,
                    "frameWidth": 192,
                    "frameHeight": 208,
                }
                (pet_dir / "pet.json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

        # 写入数据库
        db = get_db()
        display_name = pet_info.get("displayName", slug)
        db.execute(
            """INSERT OR IGNORE INTO pets
               (name, display_name, description, source_url, local_path,
                frame_width, frame_height, columns, rows)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (slug, display_name, pet_info.get("kind", ""),
             sheet_url, str(pet_dir), 192, 208, 9, 8),
        )
        pet_id = db.execute("SELECT id FROM pets WHERE name = ?", (slug,)).fetchone()[0]
        db.execute("INSERT OR IGNORE INTO pet_state (pet_id) VALUES (?)", (pet_id,))
        db.commit()
        db.close()

        size_kb = (pet_dir / "spritesheet.webp").stat().st_size // 1024
        return {"success": True, "pet": slug, "display_name": display_name, "size_kb": size_kb}

    except HTTPException:
        raise
    except Exception as e:
        import shutil
        shutil.rmtree(pet_dir, ignore_errors=True)
        raise HTTPException(500, f"下载失败: {str(e)}")


@router.get("/search")
async def search_pets(q: str = ""):
    """搜索宠物"""
    manifest = _load_manifest()
    pets = manifest.get("pets", [])
    if not q:
        return {"items": pets[:24], "total": len(pets)}
    q_lower = q.lower()
    results = [
        p for p in pets
        if q_lower in p.get("slug", "").lower()
        or q_lower in p.get("displayName", "").lower()
        or q_lower in p.get("kind", "").lower()
        or q_lower in p.get("submittedBy", "").lower()
    ]
    return {"items": results[:24], "total": len(results)}


def _load_manifest() -> dict:
    """加载 manifest（优先本地缓存）"""
    if MANIFEST_CACHE.exists():
        try:
            data = json.loads(MANIFEST_CACHE.read_text(encoding="utf-8"))
            if data and data.get("pets"):
                return data
        except (json.JSONDecodeError, IOError):
            pass
    # 返回空 manifest（需要用户点刷新）
    return {"total": 0, "pets": []}
