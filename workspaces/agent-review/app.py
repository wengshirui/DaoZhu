"""
Agent 复盘工作区 — 轻量挂载到主进程
展示 AI 自我复盘报告和优化建议
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes import router

FRONTEND_DIR = Path(__file__).parent / "frontend"

app = FastAPI(title="Agent 复盘")
app.include_router(router, prefix="/api")
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")
