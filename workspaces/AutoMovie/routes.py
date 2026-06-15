"""
火柴人剧场 — API 路由
功能：生成动画、列出作品、导出、GLM 配置管理
"""

import json
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from generator import generate_timeline, render_html
from glm_config import load_config, save_config, GLMConfig

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class GenerateRequest(BaseModel):
    text: str
    title: str = ""


router = APIRouter()


@router.post("/generate")
async def generate_animation(req: GenerateRequest):
    """从文本生成动画 HTML"""
    if not req.text.strip():
        raise HTTPException(400, "文本不能为空")
    if len(req.text) > 5000:
        raise HTTPException(400, "文本过长（最多 5000 字）")

    title = req.title or req.text[:20].strip()

    # 调用 AI 生成时间轴
    try:
        timeline_data = await generate_timeline(req.text)
    except Exception as e:
        raise HTTPException(500, f"AI 生成失败: {str(e)}")

    # 渲染为 HTML 文件
    filename = f"{int(time.time())}_{_safe_filename(title)}.html"
    html_content = render_html(title, timeline_data)
    output_path = OUTPUT_DIR / filename
    output_path.write_text(html_content, encoding="utf-8")

    return {
        "success": True,
        "filename": filename,
        "title": title,
        "chars": timeline_data.get("chars", {}),
        "duration": _calc_duration(timeline_data.get("timeline", [])),
    }


@router.post("/upload")
async def upload_text(file: UploadFile = File(...)):
    """上传 txt 文件"""
    if not file.filename.endswith(".txt"):
        raise HTTPException(400, "只支持 .txt 文件")
    content = await file.read()
    text = content.decode("utf-8")
    title = file.filename.replace(".txt", "")
    return {"text": text, "title": title}


@router.get("/works")
async def list_works():
    """列出已生成的作品"""
    works = []
    for f in sorted(OUTPUT_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        works.append({
            "filename": f.name,
            "title": f.stem.split("_", 1)[-1] if "_" in f.stem else f.stem,
            "size": f.stat().st_size,
            "created": int(f.stat().st_mtime),
        })
    return {"works": works}


@router.delete("/works/{filename}")
async def delete_work(filename: str):
    """删除作品"""
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "作品不存在")
    path.unlink()
    return {"success": True}


def _safe_filename(s: str) -> str:
    """生成安全文件名"""
    s = re.sub(r'[^\w\u4e00-\u9fff]', '', s)
    return s[:30] or "untitled"


def _calc_duration(timeline: list) -> int:
    """计算动画总时长（毫秒）"""
    if not timeline:
        return 0
    return max(ev.get("t", 0) for ev in timeline)


# === GLM 配置 API（#083）===

class GLMConfigRequest(BaseModel):
    api_key: str = ""
    enabled: bool = False
    image_model: str = "cogview-4"
    tts_model: str = "glm-tts"


@router.get("/glm/config")
async def get_glm_config():
    """获取 GLM 配置状态（不暴露完整 Key）"""
    config = load_config()
    return {
        "enabled": config.enabled,
        "has_key": bool(config.api_key),
        "key_preview": config.api_key[:8] + "***" if config.api_key else "",
        "image_model": config.image_model,
        "tts_model": config.tts_model,
        "is_ready": config.is_ready,
    }


@router.post("/glm/config")
async def update_glm_config(req: GLMConfigRequest):
    """更新 GLM 配置"""
    config = GLMConfig(
        api_key=req.api_key,
        enabled=req.enabled,
        image_model=req.image_model,
        tts_model=req.tts_model,
    )
    save_config(config)
    return {"success": True, "is_ready": config.is_ready}


@router.post("/glm/test")
async def test_glm_connection():
    """测试 GLM API 连接是否可用"""
    config = load_config()
    if not config.api_key:
        raise HTTPException(400, "未配置 API Key")

    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 简单调用 models 列表接口测试连通性
            resp = await client.get(
                f"{config.base_url}/models",
                headers={"Authorization": f"Bearer {config.api_key}"},
            )
            if resp.status_code == 200:
                return {"success": True, "message": "连接正常"}
            else:
                return {"success": False, "message": f"API 返回 {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)[:100]}"}


# === Pipeline API（#083 三级模式视频生成）===

class PipelineRequest(BaseModel):
    text: str
    title: str = ""
    mode: str = "auto"  # auto / simple / medium / advanced
    resolution: str = "1920x1080"  # 1920x1080 / 1080x1920 / 1080x1080
    stop_at: str = "video"  # storyboard / assets / video


@router.post("/generate/video")
async def generate_video(req: PipelineRequest):
    """
    三级模式视频生成（#083 核心 API）。
    支持 stop_at 阶段可停：storyboard → assets → video
    """
    if not req.text.strip():
        raise HTTPException(400, "文本不能为空")
    if len(req.text) > 10000:
        raise HTTPException(400, "文本过长（最多 10000 字）")

    from pipeline import run_pipeline

    result = await run_pipeline(
        text=req.text.strip(),
        title=req.title or req.text[:20].strip(),
        mode=req.mode,
        resolution=req.resolution,
        stop_at=req.stop_at,
    )

    return result


@router.get("/generate/mode")
async def get_current_mode():
    """获取当前可用的最高模式"""
    from pipeline import detect_mode
    mode = detect_mode()
    return {
        "mode": mode,
        "description": {
            "simple": "简单模式 — SVG 无声 HTML（零成本）",
            "medium": "中级模式 — Pexels 视频背景 + Edge-TTS 配音（免费）",
            "advanced": "高级模式 — GLM-Image 插图 + GLM-TTS 克隆配音（最优质）",
        }.get(mode, "未知"),
    }


# === Pexels 配置 API ===

class PexelsConfigRequest(BaseModel):
    api_keys: list[str] = []


@router.get("/pexels/config")
async def get_pexels_config():
    """获取 Pexels 配置状态"""
    config_path = Path(__file__).parent / "pexels_config.json"
    if not config_path.exists():
        return {"has_keys": False, "key_count": 0}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        keys = data.get("api_keys", [])
        return {
            "has_keys": bool(keys),
            "key_count": len(keys),
            "key_previews": [k[:8] + "***" for k in keys],
        }
    except Exception:
        return {"has_keys": False, "key_count": 0}


@router.post("/pexels/config")
async def update_pexels_config(req: PexelsConfigRequest):
    """更新 Pexels API Key 配置"""
    config_path = Path(__file__).parent / "pexels_config.json"
    data = {"api_keys": [k.strip() for k in req.api_keys if k.strip()]}
    config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"success": True, "key_count": len(data["api_keys"])}


@router.get("/works/videos")
async def list_video_works():
    """列出已生成的视频作品"""
    works = []
    for f in sorted(OUTPUT_DIR.glob("*_final*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        works.append({
            "filename": f.name,
            "title": f.stem.split("_", 1)[-1] if "_" in f.stem else f.stem,
            "size": f.stat().st_size,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
            "created": int(f.stat().st_mtime),
        })
    # 也包含带字幕的版本
    for f in sorted(OUTPUT_DIR.glob("*_subtitled*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        works.append({
            "filename": f.name,
            "title": f.stem.split("_", 1)[-1] if "_" in f.stem else f.stem,
            "size": f.stat().st_size,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
            "created": int(f.stat().st_mtime),
        })
    return {"works": works}
