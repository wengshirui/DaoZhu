"""宠物商店 — 对接 codex-pet.org 真实宠物数据"""

import json
import re
import httpx
from pathlib import Path
from fastapi import APIRouter, HTTPException

from db import get_db

router = APIRouter()

PETS_DIR = Path(__file__).parent.parent / "pets"
CATALOG_CACHE = Path(__file__).parent.parent / "pets" / "_catalog.json"
ASSETS_BASE = "https://assets.codex-pet.org"
SITE_BASE = "https://codex-pet.org"


@router.get("/catalog")
async def get_catalog(page: int = 1, per_page: int = 12, tag: str = ""):
    """获取宠物商店目录"""
    catalog = _load_catalog()
    if tag:
        tag_lower = tag.lower()
        catalog = [p for p in catalog if tag_lower in [t.lower() for t in p.get("tags", [])]]
    total = len(catalog)
    start = (page - 1) * per_page
    end = start + per_page
    items = catalog[start:end]
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": items,
    }


@router.get("/tags")
async def get_tags():
    """获取所有可用标签"""
    catalog = _load_catalog()
    tag_count = {}
    for p in catalog:
        for t in p.get("tags", []):
            tag_count[t] = tag_count.get(t, 0) + 1
    sorted_tags = sorted(tag_count.items(), key=lambda x: -x[1])
    return [{"name": t, "count": c} for t, c in sorted_tags[:30]]


@router.get("/search")
async def search_catalog(q: str = ""):
    """搜索宠物目录"""
    catalog = _load_catalog()
    if not q:
        return {"items": catalog[:12], "total": len(catalog)}
    q_lower = q.lower()
    results = [
        p for p in catalog
        if q_lower in p.get("name", "").lower()
        or q_lower in p.get("display_name", "").lower()
        or q_lower in p.get("description", "").lower()
        or q_lower in " ".join(p.get("tags", [])).lower()
    ]
    return {"items": results[:24], "total": len(results)}


@router.post("/refresh")
async def refresh_catalog():
    """从 codex-pet.org 刷新宠物目录"""
    try:
        pets = await _scrape_codex_pet_gallery()
        if pets:
            CATALOG_CACHE.parent.mkdir(parents=True, exist_ok=True)
            CATALOG_CACHE.write_text(
                json.dumps(pets, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return {"success": True, "count": len(pets)}
    except Exception as e:
        return {"success": False, "message": f"刷新失败: {str(e)}"}
    return {"success": False, "message": "未获取到数据"}


@router.post("/download/{pet_name}")
async def download_pet(pet_name: str):
    """下载宠物资源到本地"""
    pet_dir = PETS_DIR / pet_name
    if pet_dir.exists():
        raise HTTPException(400, f"宠物 {pet_name} 已存在")

    # 从目录中找到该宠物的信息
    catalog = _load_catalog()
    pet_info = next((p for p in catalog if p["name"] == pet_name), None)
    if not pet_info:
        raise HTTPException(404, f"宠物 {pet_name} 不在目录中")

    pet_dir.mkdir(parents=True, exist_ok=True)
    spritesheet_url = pet_info.get("spritesheet_url", "")

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            # 下载 spritesheet
            if spritesheet_url:
                resp = await client.get(spritesheet_url)
                if resp.status_code == 200:
                    (pet_dir / "spritesheet.webp").write_bytes(resp.content)
                else:
                    raise HTTPException(404, "spritesheet 下载失败")

            # 生成 pet.json
            pet_json = {
                "name": pet_info.get("display_name", pet_name),
                "description": pet_info.get("description", ""),
                "spritesheet": "spritesheet.webp",
                "columns": 8,
                "rows": 9,
                "frameWidth": 192,
                "frameHeight": 208,
                "source": pet_info.get("url", ""),
                "creator": pet_info.get("creator", ""),
                "tags": pet_info.get("tags", []),
            }
            (pet_dir / "pet.json").write_text(
                json.dumps(pet_json, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # 写入数据库
        db = get_db()
        db.execute(
            """INSERT INTO pets (name, display_name, description, source_url, local_path,
               frame_width, frame_height, columns, rows)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pet_name,
                pet_info.get("display_name", pet_name),
                pet_info.get("description", ""),
                spritesheet_url,
                str(pet_dir),
                192, 208, 8, 9,
            ),
        )
        pet_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("INSERT INTO pet_state (pet_id) VALUES (?)", (pet_id,))
        db.commit()
        db.close()

        return {"success": True, "pet": pet_name}

    except HTTPException:
        raise
    except Exception as e:
        import shutil
        shutil.rmtree(pet_dir, ignore_errors=True)
        raise HTTPException(500, f"下载失败: {str(e)}")


async def _scrape_codex_pet_gallery() -> list:
    """爬取 codex-pet.org 首页宠物列表（多页）"""
    pets = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # 爬取前 5 页（约 60 只宠物，够用了）
        for page_num in range(1, 6):
            url = f"{SITE_BASE}/zh/" if page_num == 1 else f"{SITE_BASE}/zh/?page={page_num}"
            resp = await client.get(url)
            if resp.status_code != 200:
                break
            page_pets = _parse_gallery_html(resp.text)
            if not page_pets:
                break
            pets.extend(page_pets)
    return pets


def _parse_gallery_html(html: str) -> list:
    """从 HTML 中解析宠物列表"""
    pets = []
    # 匹配宠物卡片中的 spritesheet URL 和链接
    # 模式: /zh/pets/{name}/ 和 assets.codex-pet.org/{creator-id}/{name}/spritesheet.webp
    pet_links = re.findall(r'/zh/pets/([a-z0-9_-]+)/', html)
    sprite_urls = re.findall(
        r'(https://assets\.codex-pet\.org/[a-f0-9-]+/([a-z0-9_-]+)/spritesheet\.webp)',
        html
    )

    # 提取描述和标题（简化解析）
    # 匹配 heading 后面的文本
    titles = re.findall(r'<h2[^>]*>([^<]+)</h2>', html)

    # 构建 URL 映射
    url_map = {}
    for full_url, name in sprite_urls:
        url_map[name] = full_url

    seen = set()
    for name in pet_links:
        if name in seen or name not in url_map:
            continue
        seen.add(name)
        # 找对应标题
        display_name = name
        for t in titles:
            if name.replace('-', ' ') in t.lower() or name in t.lower():
                display_name = t.strip()
                break

        pets.append({
            "name": name,
            "display_name": display_name,
            "description": "",
            "spritesheet_url": url_map[name],
            "url": f"{SITE_BASE}/zh/pets/{name}/",
            "creator": "",
            "tags": [],
        })

    return pets


def _load_catalog() -> list:
    """加载宠物目录（优先本地缓存）"""
    if CATALOG_CACHE.exists():
        try:
            data = json.loads(CATALOG_CACHE.read_text(encoding="utf-8"))
            if data:
                return data
        except (json.JSONDecodeError, IOError):
            pass
    return _builtin_catalog()


def _builtin_catalog() -> list:
    """内置热门宠物列表（离线可用，含真实 spritesheet URL）"""
    return [
        {
            "name": "ikkun",
            "display_name": "ikkun",
            "description": "灰色刘海、圆眼红腮、穿黑色背带裤的团雀风数字宠物",
            "spritesheet_url": f"{ASSETS_BASE}/3b850755-717a-4cbf-b2fe-3c2589c6cd39/ikkun/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/ikkun/",
            "creator": "Community",
            "tags": ["Pet", "Cute"],
        },
        {
            "name": "fluffy-pup",
            "display_name": "大顺狗",
            "description": "A soft white puppy with rosy cheeks and bouncy energy",
            "spritesheet_url": f"{ASSETS_BASE}/4bf39d63-ee48-48e2-b316-4a87be4bc45b/fluffy-pup/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/fluffy-pup/",
            "creator": "holmex",
            "tags": ["Dog", "Animal", "Cute"],
        },
        {
            "name": "goku-forms",
            "display_name": "Goku Forms",
            "description": "A compact chibi Goku pet that transforms between Dragon Ball forms",
            "spritesheet_url": f"{ASSETS_BASE}/35635fde-ecf9-4296-a6e2-ab866b4f5607/goku-forms/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/goku-forms/",
            "creator": "cky",
            "tags": ["Pet", "Anime"],
        },
        {
            "name": "hinata-shimeji",
            "display_name": "Hinata Shimeji",
            "description": "A compact transparent Shimeji-style Hinata desktop pet",
            "spritesheet_url": f"{ASSETS_BASE}/f6ff0f83-9231-48c1-b47d-c25d06cd3e37/hinata-shimeji/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/hinata-shimeji/",
            "creator": "sept",
            "tags": ["Pet", "Person", "Cute"],
        },
        {
            "name": "table-laugh-girl",
            "display_name": "豆包",
            "description": "A compact 3D toy-style desktop pet with a dialogue reaction state",
            "spritesheet_url": f"{ASSETS_BASE}/3cda724c-c5e1-4a86-84f6-9065f1aa7cd3/table-laugh-girl/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/table-laugh-girl/",
            "creator": "yubo",
            "tags": ["Pet", "Person", "AI"],
        },
        {
            "name": "red-tie-pixel-dancer",
            "display_name": "Trump",
            "description": "A compact pixel-art chibi suited blond red-tie dancer",
            "spritesheet_url": f"{ASSETS_BASE}/9c8eb934-818e-4599-8b87-1389aef2c9d1/red-tie-pixel-dancer/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/red-tie-pixel-dancer/",
            "creator": "wilson",
            "tags": ["Person", "Pet", "Funny"],
        },
        {
            "name": "xiao-ikun",
            "display_name": "小 ikun",
            "description": "两岁半的小 ikun，擅长唱、跳、rap 和篮球",
            "spritesheet_url": f"{ASSETS_BASE}/10361898-2182-49f6-811e-07cafcfea89f/xiao-ikun/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/xiao-ikun/",
            "creator": "lebron",
            "tags": ["Pet", "Funny", "Animal"],
        },
        {
            "name": "ogiso-setsuna",
            "display_name": "ogiso-setsuna",
            "description": "High-restoration chibi school-uniform Setsuna",
            "spritesheet_url": f"{ASSETS_BASE}/fd826270-ad5f-4ceb-9681-63ee755276c8/ogiso-setsuna/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/ogiso-setsuna/",
            "creator": "yjjjjj",
            "tags": ["Pet", "Person", "Cute"],
        },
        {
            "name": "saaya-star",
            "display_name": "Saaya-BangDream",
            "description": "Would you like to eat bread together?",
            "spritesheet_url": f"{ASSETS_BASE}/68a51dfc-c9e7-4565-9959-64f6fc39ca4c/saaya-star/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/saaya-star/",
            "creator": "h-o-oh",
            "tags": ["Pet", "Person"],
        },
        {
            "name": "stage-hat",
            "display_name": "easonchan mos",
            "description": "A compact pixel-art chibi stage performer with neon-pink hat",
            "spritesheet_url": f"{ASSETS_BASE}/9c8eb934-818e-4599-8b87-1389aef2c9d1/stage-hat/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/stage-hat/",
            "creator": "wilson",
            "tags": ["Person", "Pet", "Cute"],
        },
        {
            "name": "kurobraid",
            "display_name": "Kurobraid",
            "description": "A compact chibi anime girl with black side-swept bangs and side braid",
            "spritesheet_url": f"{ASSETS_BASE}/ffb4e665-2f52-42ac-8037-879504c57418/kurobraid/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/kurobraid/",
            "creator": "lzh0",
            "tags": ["Pet", "Anime"],
        },
        {
            "name": "ahri-star-guardian",
            "display_name": "星之守护者阿狸",
            "description": "3D半Q全身星之守护者阿狸桌面宠物",
            "spritesheet_url": f"{ASSETS_BASE}/35dbd2d8-0923-4e19-b171-8494a9b2ca71/ahri-star-guardian/spritesheet.webp",
            "url": f"{SITE_BASE}/zh/pets/ahri-star-guardian/",
            "creator": "kuru",
            "tags": ["Pet", "Fantasy"],
        },
    ]
