"""
桌面宠物 — 工作区入口
端口: 7805
功能: 宠物商店、宠物管理、互动、状态系统
"""

import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes import store_router, pets_router, interact_router

DB_PATH = Path(__file__).parent / "data.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
FRONTEND_DIR = Path(__file__).parent / "frontend"
PETS_DIR = Path(__file__).parent / "pets"


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(str(DB_PATH))
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()


# 确保目录在模块加载时就存在（StaticFiles 需要）
PETS_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="桌面宠物", version="1.0.0", lifespan=lifespan)

# API 路由
app.include_router(store_router, prefix="/api/store", tags=["store"])
app.include_router(pets_router, prefix="/api/pets", tags=["pets"])
app.include_router(interact_router, prefix="/api/interact", tags=["interact"])

# 静态资源
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/pets", StaticFiles(directory=PETS_DIR), name="pet_assets")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/desktop/launch")
async def launch_desktop_pet():
    """启动桌面宠物窗口（独立进程）"""
    import subprocess
    import sys
    from fastapi import HTTPException

    script = Path(__file__).parent / "desktop_window.py"
    if not script.exists():
        raise HTTPException(500, "desktop_window.py 不存在")

    # 找到带 PySide6 的 python
    # 优先用项目根目录的 .venv（PySide6 装在那里）
    # 用 pythonw.exe 启动以隐藏 cmd 窗口
    project_root = Path(__file__).parent.parent.parent
    venv_pythonw = project_root / ".venv" / "Scripts" / "pythonw.exe"
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if venv_pythonw.exists():
        exe = venv_pythonw  # 无 cmd 窗口
    elif venv_python.exists():
        exe = venv_python
    else:
        exe = Path(sys.executable)

    try:
        # 以独立进程启动，不阻塞 Web 服务
        subprocess.Popen(
            [str(exe), str(script)],
            cwd=str(script.parent),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            if sys.platform == "win32" else 0,
            start_new_session=True,
        )
        return {"success": True, "message": "桌面宠物已启动，查看系统托盘 🐾"}
    except Exception as e:
        raise HTTPException(500, f"启动失败: {e}")


@app.get("/api/proxy/spritesheet")
async def proxy_spritesheet(url: str):
    """代理远程 spritesheet 图片（绕过 CORS）"""
    import httpx
    # 允许所有 HTTPS 图片资源（宠物来源多样）
    if not url.startswith("https://"):
        from fastapi import HTTPException
        raise HTTPException(400, "仅支持 HTTPS 资源")
    # 基本安全检查：必须是图片类 URL
    if not any(url.endswith(ext) for ext in ('.webp', '.png', '.gif', '.jpg', '.jpeg')):
        # 也允许 UploadThing 等无扩展名的 URL
        pass
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            from fastapi import HTTPException
            raise HTTPException(resp.status_code, "资源加载失败")
        from fastapi.responses import Response
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/webp"),
            headers={"Cache-Control": "public, max-age=604800"},
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7805)
