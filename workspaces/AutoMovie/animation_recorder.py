"""
火柴人剧场 — 动画录制服务（#083 Stage 3）
使用 Playwright 将 HTML 动画录制为视频片段。

流程：
1. 生成带背景图/视频的增强版 HTML
2. 用 Playwright 打开并录制为 webm
3. ffmpeg 转码为 mp4 片段

如果 Playwright 不可用，降级到静态图+音频方案。
"""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from storyboard import Storyboard, StoryboardFrame
from generator import render_html

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output" / "segments"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_playwright() -> bool:
    """检查 Playwright 是否可用。"""
    try:
        from playwright.async_api import async_playwright
        return True
    except ImportError:
        return False


async def record_animation(
    storyboard: Storyboard,
    resolution: str = "1920x1080",
) -> list[str]:
    """
    录制整个分镜的动画为视频片段列表。

    Args:
        storyboard: 完整分镜（含 timeline 数据）
        resolution: 输出分辨率

    Returns:
        视频片段路径列表（每帧一个 mp4）
    """
    if not check_playwright():
        logger.warning("[Recorder] Playwright 不可用，使用静态方案")
        return await _fallback_static_segments(storyboard, resolution)

    try:
        return await _record_with_playwright(storyboard, resolution)
    except Exception as e:
        logger.error(f"[Recorder] Playwright 录制失败: {e}")
        return await _fallback_static_segments(storyboard, resolution)


async def _record_with_playwright(
    storyboard: Storyboard,
    resolution: str,
) -> list[str]:
    """用 Playwright 录制 HTML 动画。"""
    from playwright.async_api import async_playwright

    w, h = [int(x) for x in resolution.split("x")]

    # 生成完整 HTML（含所有帧的时间轴）
    timeline_data = _storyboard_to_timeline(storyboard)
    html_content = render_html(storyboard.title, timeline_data)

    # 写入临时 HTML
    html_path = OUTPUT_DIR / f"{storyboard.title[:20]}_anim.html"
    html_path.write_text(html_content, encoding="utf-8")

    # 计算总时长
    total_duration_ms = sum(
        int(f.duration * 1000) for f in storyboard.frames
    ) or 30000  # 默认 30 秒

    # Playwright 录制
    webm_path = OUTPUT_DIR / f"{storyboard.title[:20]}_full.webm"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={"width": w, "height": h},
        )
        page = await context.new_page()
        await page.set_viewport_size({"width": w, "height": h})
        await page.goto(f"file:///{html_path.absolute()}")

        # 等待动画播放完成
        await page.wait_for_timeout(total_duration_ms + 2000)

        await page.close()
        await context.close()
        await browser.close()

    # 找到录制的 webm 文件
    webm_files = list(OUTPUT_DIR.glob("*.webm"))
    if not webm_files:
        logger.warning("[Recorder] 未找到录制文件")
        return await _fallback_static_segments(storyboard, resolution)

    # 取最新的 webm
    latest_webm = max(webm_files, key=lambda f: f.stat().st_mtime)

    # 转码为 mp4
    mp4_path = str(OUTPUT_DIR / f"{storyboard.title[:20]}_full.mp4")
    if _webm_to_mp4(str(latest_webm), mp4_path):
        # 清理 webm
        latest_webm.unlink(missing_ok=True)
        html_path.unlink(missing_ok=True)
        return [mp4_path]

    return await _fallback_static_segments(storyboard, resolution)


async def _fallback_static_segments(
    storyboard: Storyboard,
    resolution: str,
) -> list[str]:
    """
    降级方案：每帧用背景图（或黑底）+ 音频生成视频片段。
    """
    if not shutil.which("ffmpeg"):
        return []

    w, h = resolution.split("x")
    segments = []

    for frame in storyboard.frames:
        segment_path = str(OUTPUT_DIR / f"seg_{frame.index:03d}.mp4")

        # 用实际音频时长（精确同步）
        if frame.audio_path and Path(frame.audio_path).exists():
            import subprocess as _sp
            import re as _re
            try:
                _r = _sp.run(["ffmpeg", "-i", frame.audio_path, "-f", "null", "-"],
                             capture_output=True, text=True, timeout=10)
                _m = _re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", _r.stderr)
                if _m:
                    _h, _min, _s = _m.groups()
                    frame.duration = int(_h)*3600 + int(_min)*60 + float(_s)
            except Exception:
                pass

        duration = frame.duration or 3.0

        if frame.image_path and Path(frame.image_path).exists() and frame.image_path.endswith(".mp4"):
            # Pexels 视频背景 → 裁剪到帧时长
            cmd = [
                "ffmpeg", "-y",
                "-i", frame.image_path,
                "-t", f"{duration:.2f}",
                "-c:v", "libx264",
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                       f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
                "-pix_fmt", "yuv420p", "-an",
                segment_path,
            ]
        elif frame.image_path and Path(frame.image_path).exists():
            # 静态图片（GLM-Image 或其他）→ 图片循环
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", frame.image_path,
                "-t", f"{duration:.2f}",
                "-c:v", "libx264", "-tune", "stillimage",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                       f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
                segment_path,
            ]
        else:
            # 黑底
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d={duration:.2f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                segment_path,
            ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if Path(segment_path).exists():
                segments.append(segment_path)
                frame.video_segment = segment_path
        except Exception as e:
            logger.warning(f"[Recorder] 帧 {frame.index} 片段生成失败: {e}")

    logger.info(f"[Recorder] 生成 {len(segments)} 个视频片段（静态方案）")
    return segments


def _storyboard_to_timeline(storyboard: Storyboard) -> dict:
    """将分镜转回 timeline 格式（供 HTML 模板使用）。"""
    chars = {}
    for c in storyboard.characters:
        chars[c.name] = {"color": c.color, "label": c.name, "scale": 1}

    timeline = []
    t = 0
    for frame in storyboard.frames:
        if frame.narration:
            if frame.speaker and frame.speaker != "narrator":
                timeline.append({
                    "t": t, "action": "dialogue",
                    "who": frame.speaker, "text": frame.narration,
                })
            else:
                timeline.append({
                    "t": t, "action": "narr", "text": frame.narration,
                })
        t += int((frame.duration or 3.0) * 1000)

    timeline.append({"t": t, "action": "end"})
    return {"chars": chars, "timeline": timeline}


def _webm_to_mp4(webm_path: str, mp4_path: str) -> bool:
    """将 webm 转码为 mp4。"""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", webm_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                mp4_path,
            ],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0 and Path(mp4_path).exists()
    except Exception:
        return False
