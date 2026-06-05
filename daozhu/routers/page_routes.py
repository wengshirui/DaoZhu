import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# 静态文件目录（与 app.py 保持一致）
if getattr(sys, "frozen", False):
    FRONTEND_DIR = Path(sys._MEIPASS) / "daozhu" / "frontend"
else:
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# === 页面路由 ===
@router.get("/")
async def index():
    """返回主界面（未配置且未跳过引导时跳转引导页）"""
    from fastapi import Request
    from daozhu.config import get_api_key, ENV_FILE, PLATFORM_ROOT

    # 检查是否已跳过引导（config.json 中标记）
    config_file = PLATFORM_ROOT / "config.json"
    skipped = False
    if config_file.exists():
        import json as _json
        try:
            cfg = _json.loads(config_file.read_text(encoding="utf-8"))
            skipped = cfg.get("onboarding_skipped", False)
        except Exception:
            pass

    # 未配置 API Key 且未跳过 → 跳转引导
    if not skipped and (not ENV_FILE.exists() or not get_api_key()):
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/onboarding")

    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/favicon.svg")
async def favicon():
    """返回 favicon SVG"""
    return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")


@router.get("/favicon.ico")
async def favicon_ico():
    """返回 favicon ICO"""
    ico_path = FRONTEND_DIR / "favicon.ico"
    if ico_path.exists():
        return FileResponse(ico_path, media_type="image/x-icon")
    return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")


@router.get("/onboarding")
async def onboarding_page():
    """引导页面"""
    return FileResponse(FRONTEND_DIR / "onboarding.html")


@router.get("/loading.html")
async def loading_page():
    """启动加载页（Tauri 壳用）"""
    return FileResponse(FRONTEND_DIR / "loading.html")


@router.get("/pet.html")
async def pet_page():
    """桌面宠物页面（Tauri 透明窗口用）"""
    return FileResponse(FRONTEND_DIR / "pet.html")


@router.post("/api/onboarding/save-key")
async def save_api_key(body: dict):
    """保存 API Key 到 config.db + .env"""
    key = body.get("key", "").strip()
    if not key:
        raise HTTPException(400, "Key 不能为空")

    # 写入 config.db
    from daozhu.config_db import set_secret
    set_secret("DEEPSEEK_API_KEY", key)

    # 同时写入 .env（向后兼容）
    from daozhu.config import PLATFORM_ROOT
    env_path = PLATFORM_ROOT / ".env"
    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")

    lines = existing.split("\n")
    found = False
    for i, line in enumerate(lines):
        if line.startswith("DEEPSEEK_API_KEY="):
            lines[i] = f"DEEPSEEK_API_KEY={key}"
            found = True
            break
    if not found:
        lines.append(f"DEEPSEEK_API_KEY={key}")

    env_path.write_text("\n".join(lines), encoding="utf-8")
    return {"success": True}


@router.post("/api/onboarding/save-gitee-token")
async def save_gitee_token(body: dict):
    """保存 Gitee Token 到 config.db + .env"""
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(400, "Token 不能为空")

    # 写入 config.db
    from daozhu.config_db import set_secret
    set_secret("GITEE_TOKEN", token)

    # 同时写入 .env
    from daozhu.config import PLATFORM_ROOT
    env_path = PLATFORM_ROOT / ".env"
    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")

    lines = existing.split("\n")
    found = False
    for i, line in enumerate(lines):
        if line.startswith("GITEE_TOKEN="):
            lines[i] = f"GITEE_TOKEN={token}"
            found = True
            break
    if not found:
        lines.append(f"GITEE_TOKEN={token}")

    env_path.write_text("\n".join(lines), encoding="utf-8")
    return {"success": True}


@router.post("/api/onboarding/save-secret")
async def save_secret_generic(body: dict):
    """通用密钥保存接口"""
    name = body.get("name", "").strip()
    value = body.get("value", "").strip()
    if not name or not value:
        raise HTTPException(400, "name 和 value 不能为空")

    from daozhu.config_db import set_secret
    set_secret(name, value)
    return {"success": True}


@router.delete("/api/config/secrets/{name}")
async def delete_secret_endpoint(name: str):
    """删除密钥配置"""
    from daozhu.config_db import delete_secret
    deleted = delete_secret(name)
    if not deleted:
        raise HTTPException(status_code=404, detail="密钥不存在")
    return {"success": True}


@router.get("/api/providers")
async def get_providers():
    """获取可用的 AI 模型提供商列表"""
    from daozhu.config import PROVIDERS, get_config_value
    current = get_config_value("ai.provider", "deepseek")
    result = []
    for pid, info in PROVIDERS.items():
        result.append({
            "id": pid,
            "name": info["name"],
            "needs_key": info["needs_key"],
            "active": pid == current,
        })
    return {"providers": result, "current": current}




