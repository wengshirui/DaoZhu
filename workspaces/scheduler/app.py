"""
定时任务工作区 — 轻量挂载到主进程
提供定时任务管理页面 + API 路由
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes import router

FRONTEND_DIR = Path(__file__).parent / "frontend"

app = FastAPI(title="定时任务")
app.include_router(router, prefix="/api")
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")
