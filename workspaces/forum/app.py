"""
岛主论坛 — 工作区入口
端口: 7802
对接 Gitee Issues 作为论坛服务
"""

import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes import router as api_router

DB_PATH = Path(__file__).parent / "data.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
FRONTEND_DIR = Path(__file__).parent / "frontend"


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="岛主论坛", version="1.0.0", lifespan=lifespan)

# 确保数据库初始化（轻挂载时 lifespan 不会被调用）
init_db()

app.include_router(api_router, prefix="/api")
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7802)
