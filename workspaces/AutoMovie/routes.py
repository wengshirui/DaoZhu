"""
火柴人剧场 — API 路由
功能：生成动画、列出作品、导出
"""

import json
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from generator import generate_timeline, render_html

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
