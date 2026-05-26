from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn
import sys

sys.path.insert(0, str(Path(__file__).parent))
from weather_api import fetch_weather, fetch_forecast
from db import init_db, save_search, get_recent_searches, add_favorite, remove_favorite, get_favorites, is_favorite

app = FastAPI(title="天气预报")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent / "frontend"

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = FRONTEND_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>天气预报工作区</h1><p>前端页面未找到</p>")

# ========== 天气查询 API ==========

@app.get("/api/weather/current")
async def get_current_weather(city: str = Query(..., description="城市名称，如 nanjing")):
    """查询实时天气"""
    result = await fetch_weather(city)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    save_search(city)
    return result

@app.get("/api/weather/forecast")
async def get_weather_forecast(city: str = Query(..., description="城市名称"), days: int = Query(3, ge=1, le=7)):
    """查询天气预报"""
    result = await fetch_forecast(city, days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    save_search(city)
    return result

# ========== 搜索历史 & 收藏 ==========

@app.get("/api/searches")
async def recent_searches():
    """最近搜索记录"""
    return get_recent_searches()

@app.get("/api/favorites")
async def list_favorites():
    """收藏城市列表"""
    return get_favorites()

@app.post("/api/favorites")
async def add_fav(city: str = Query(...), country: str = "CN"):
    """添加收藏城市"""
    ok = add_favorite(city, country)
    if not ok:
        raise HTTPException(status_code=409, detail="该城市已收藏")
    return {"message": "收藏成功", "city": city}

@app.delete("/api/favorites")
async def remove_fav(city: str = Query(...), country: str = "CN"):
    """取消收藏城市"""
    remove_favorite(city, country)
    return {"message": "已取消收藏"}

@app.get("/api/favorites/check")
async def check_fav(city: str = Query(...), country: str = "CN"):
    """检查是否已收藏"""
    return {"is_favorite": is_favorite(city, country)}

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "7805"))
    uvicorn.run(app, host="0.0.0.0", port=port)
