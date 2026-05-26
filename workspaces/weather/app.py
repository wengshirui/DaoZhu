import os
import sys
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_db, init_db

app = FastAPI()

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

@app.on_event("startup")
async def startup():
    init_db("weather")
    # 创建历史记录表
    conn = get_db("weather")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            country TEXT,
            temp_c REAL,
            condition_text TEXT,
            humidity INTEGER,
            wind_kph REAL,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/{path:path}")
async def static_files(path: str):
    file_path = FRONTEND_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/api/weather/{city}")
async def get_weather(city: str):
    """从 wttr.in 获取天气数据"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 使用 wttr.in 的 JSON 格式
            resp = await client.get(f"https://wttr.in/{city}?format=j1")
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail=f"未找到城市: {city}")
            
            data = resp.json()
            current = data["current_condition"][0]
            location = data["nearest_area"][0]
            
            weather_info = {
                "city": location["areaName"][0]["value"],
                "country": location["country"][0]["value"],
                "temp_c": float(current["temp_C"]),
                "temp_f": float(current["temp_F"]),
                "feels_like_c": float(current["FeelsLikeC"]),
                "feels_like_f": float(current["FeelsLikeF"]),
                "condition": current["weatherDesc"][0]["value"],
                "humidity": int(current["humidity"]),
                "wind_kph": float(current["windspeedKmph"]),
                "wind_dir": current["winddir16Point"],
                "pressure": int(current["pressure"]),
                "visibility": int(current["visibility"]),
                "uv_index": int(current["uvIndex"]),
                "icon_url": f"https:{current['weatherIconUrl'][0]['value']}",
            }
            
            # 存入历史记录
            conn = get_db("weather")
            conn.execute(
                "INSERT INTO search_history (city, country, temp_c, condition_text, humidity, wind_kph) VALUES (?, ?, ?, ?, ?, ?)",
                (weather_info["city"], weather_info["country"], weather_info["temp_c"], 
                 weather_info["condition"], weather_info["humidity"], weather_info["wind_kph"])
            )
            conn.commit()
            
            return weather_info
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="天气服务请求超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/")
async def get_history(limit: int = 10):
    """获取搜索历史"""
    conn = get_db("weather")
    rows = conn.execute(
        "SELECT * FROM search_history ORDER BY searched_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(row) for row in rows]
