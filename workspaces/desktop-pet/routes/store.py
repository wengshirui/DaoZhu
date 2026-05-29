"""宠物商店 — 嵌入 codex-pet.org + 下载到本地"""

import json
import httpx
from pathlib import Path
from fastapi import APIRouter, HTTPException

from db import get_db

router = APIRouter()

PETS_DIR = Path(__file__).parent.parent / "pets"
ASSETS_BASE = "https://assets.codex-pet.org"
SITE_URL = "https://codex-pet.org/zh/"


@router.get("/site-url")
async def get_site_url():
    """返回 codex-pet.org 商店地址（前端用 iframe 嵌入）"""
    return {"url": SITE_URL}


@router.post("/download")
async def download_pet(name: str, creator_id: str = ""):
    """
    下载宠物到本地。
    - name: 宠物名称（如 ikkun、fluffy-pup）
    - creator_id: 创作者 ID（可选，用于拼接 spritesheet URL）
    如果不提供 creator_id，会尝试从 codex-pet.org 宠物页面解析。
    """
    pet_dir = PETS_DIR / name
    if pet_dir.exists() and (pet_dir / "spritesheet.webp").exists():
        raise HTTPException(400, f"宠物 '{name}' 已存在本地")

    pet_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            spritesheet_url = ""

            # 如果提供了 creator_id，直接拼接 URL
            if creator_id:
                spritesheet_url = f"{ASSETS_BASE}/{creator_id}/{name}/spritesheet.webp"
            else:
                # 从宠物详情页解析 spritesheet URL
                spritesheet_url = await _resolve_spritesheet_url(client, name)

            if not spritesheet_url:
                raise HTTPException(404, f"无法找到宠物 '{name}' 的 spritesheet 地址")

            # 下载 spritesheet
            resp = await client.get(spritesheet_url)
            if resp.status_code != 200:
                raise HTTPException(404, f"spritesheet 下载失败 (HTTP {resp.status_code})")

            (pet_dir / "spritesheet.webp").write_bytes(resp.content)

            # 生成 pet.json
            pet_json = {
                "name": name,
                "spritesheet": "spritesheet.webp",
                "columns": 8,
                "rows": 9,
                "frameWidth": 192,
                "frameHeight": 208,
                "source": spritesheet_url,
            }
            (pet_dir / "pet.json").write_text(
                json.dumps(pet_json, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # 写入数据库
        db = get_db()
        db.execute(
            """INSERT OR IGNORE INTO pets
               (name, display_name, description, source_url, local_path,
                frame_width, frame_height, columns, rows)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, name, "", spritesheet_url, str(pet_dir), 192, 208, 8, 9),
        )
        pet_id = db.execute(
            "SELECT id FROM pets WHERE name = ?", (name,)
        ).fetchone()[0]
        db.execute("INSERT OR IGNORE INTO pet_state (pet_id) VALUES (?)", (pet_id,))
        db.commit()
        db.close()

        size_kb = len((pet_dir / "spritesheet.webp").read_bytes()) // 1024
        return {"success": True, "pet": name, "size_kb": size_kb}

    except HTTPException:
        raise
    except Exception as e:
        import shutil
        shutil.rmtree(pet_dir, ignore_errors=True)
        raise HTTPException(500, f"下载失败: {str(e)}")


@router.get("/local")
async def list_local_pets():
    """列出本地已下载的宠物（仅文件系统扫描，不查数据库）"""
    pets = []
    if not PETS_DIR.exists():
        return pets
    for pet_dir in sorted(PETS_DIR.iterdir()):
        if not pet_dir.is_dir() or pet_dir.name.startswith("_"):
            continue
        sheet = pet_dir / "spritesheet.webp"
        if not sheet.exists():
            continue
        meta = {}
        meta_path = pet_dir / "pet.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        pets.append({
            "name": pet_dir.name,
            "display_name": meta.get("name", pet_dir.name),
            "spritesheet_url": f"/pets/{pet_dir.name}/spritesheet.webp",
            "size_kb": sheet.stat().st_size // 1024,
        })
    return pets


async def _resolve_spritesheet_url(client: httpx.AsyncClient, name: str) -> str:
    """从 codex-pet.org 宠物详情页解析 spritesheet URL"""
    import re
    page_url = f"https://codex-pet.org/zh/pets/{name}/"
    try:
        resp = await client.get(page_url)
        if resp.status_code != 200:
            return ""
        # 匹配: https://assets.codex-pet.org/{uuid}/{name}/spritesheet.webp
        match = re.search(
            rf'(https://assets\.codex-pet\.org/[a-f0-9-]+/{re.escape(name)}/spritesheet\.webp)',
            resp.text,
        )
        return match.group(1) if match else ""
    except Exception:
        return ""
