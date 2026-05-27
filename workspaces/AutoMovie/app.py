"""
火柴人剧场 — 工作区入口
轻挂载模式，端口共享主平台 7788
功能：上传文本 → AI 生成时间轴 → 输出可播放 HTML
"""

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from routes import router as api_router

FRONTEND_DIR = Path(__file__).parent / "frontend"
OUTPUT_DIR = Path(__file__).parent / "output"
ASSETS_DIR = Path(__file__).parent / "assets"
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="火柴人剧场", version="1.0.0")

app.include_router(api_router, prefix="/api")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7805)