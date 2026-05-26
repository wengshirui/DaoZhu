import httpx
import json
from typing import Optional

# 使用 wttr.in 天气 API（无需 API Key，免费）
# 也支持 qweather.com 等，但需要 API Key
WEATHER_API_BASE = "https://wttr.in"

async def fetch_weather(city: str) -> dict:
    """获取指定城市的实时天气信息"""
    try:
        url = f"{WEATHER_API_BASE}/{city}?format=j1"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"error": f"无法获取天气信息，状态码: {resp.status_code}"}
            data = resp.json()
            return _parse_weather_data(data, city)
    except httpx.TimeoutException:
        return {"error": "请求超时，请稍后再试"}
    except Exception as e:
        return {"error": f"查询失败: {str(e)}"}

async def fetch_forecast(city: str, days: int = 3) -> dict:
    """获取未来几天的天气预报"""
    try:
        url = f"{WEATHER_API_BASE}/{city}?format=j1"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"error": f"无法获取预报信息，状态码: {resp.status_code}"}
            data = resp.json()
            return _parse_forecast_data(data, city, days)
    except httpx.TimeoutException:
        return {"error": "请求超时，请稍后再试"}
    except Exception as e:
        return {"error": f"查询失败: {str(e)}"}

def _parse_weather_data(data: dict, city: str) -> dict:
    """解析 wttr.in 返回的天气数据"""
    try:
        current = data["current_condition"][0]
        
        # 尝试获取城市中文名
        city_display = city
        if "nearest_area" in data and data["nearest_area"]:
            area = data["nearest_area"][0]
            area_name = area.get("areaName", [{}])[0].get("value", "")
            if area_name:
                city_display = area_name
        
        result = {
            "city": city_display,
            "query_city": city,
            "temp": current.get("temp_C", "N/A"),
            "temp_f": current.get("temp_F", "N/A"),
            "feels_like": current.get("FeelsLikeC", "N/A"),
            "humidity": current.get("humidity", "N/A"),
            "wind_speed": current.get("windspeedKmph", "N/A"),
            "wind_dir": current.get("winddir16Point", "N/A"),
            "pressure": current.get("pressure", "N/A"),
            "visibility": current.get("visibility", "N/A"),
            "cloud_cover": current.get("cloudcover", "N/A"),
            "weather_desc": current.get("weatherDesc", [{}])[0].get("value", ""),
            "weather_code": current.get("weatherCode", ""),
            "uv_index": current.get("uvIndex", "N/A"),
            "last_updated": current.get("localObsDateTime", ""),
        }
        return result
    except (KeyError, IndexError, TypeError) as e:
        return {"error": f"天气数据解析失败: {str(e)}", "raw": data}

def _parse_forecast_data(data: dict, city: str, days: int) -> dict:
    """解析预报数据"""
    try:
        current = _parse_weather_data(data, city)
        
        forecasts = []
        if "weather" in data:
            for day_data in data["weather"][:days]:
                forecasts.append({
                    "date": day_data.get("date", ""),
                    "max_temp": day_data.get("maxtempC", ""),
                    "min_temp": day_data.get("mintempC", ""),
                    "weather_desc": day_data.get("hourly", [{}])[0].get("weatherDesc", [{}])[0].get("value", ""),
                    "weather_code": day_data.get("hourly", [{}])[0].get("weatherCode", ""),
                    "sunrise": day_data.get("astronomy", [{}])[0].get("sunrise", ""),
                    "sunset": day_data.get("astronomy", [{}])[0].get("sunset", ""),
                })
        
        return {
            "current": current,
            "forecasts": forecasts,
            "city": current.get("city", city),
        }
    except Exception as e:
        return {"error": f"预报数据解析失败: {str(e)}"}
