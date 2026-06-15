"""
火柴人剧场 — 视频生成 Pipeline（#083）
编排 Stage 1-4 的完整流水线。

参考: MoneyPrinterTurbo task.py (状态机 + stop_at)
      Pixelle-Video pipelines/standard.py (阶段化设计)

支持:
- stop_at: "storyboard"（只生成分镜）/ "assets"（生成资产不合成）/ "video"（完整）
- 三级模式自动选择（根据配置的 Key 决定）
- 进度回调（AC31）
- 帧级失败隔离（AC35）
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Callable, Optional
from dataclasses import asdict

from storyboard import Storyboard, StoryboardFrame, CharacterConfig
from glm_config import load_config

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 状态常量（参考 MoneyPrinterTurbo）
STATE_PROCESSING = "processing"
STATE_COMPLETE = "complete"
STATE_FAILED = "failed"


def detect_mode() -> str:
    """
    检测当前可用的最高模式（AC1-3）。

    Returns:
        "simple" / "medium" / "advanced"
    """
    config = load_config()

    if config.api_key:
        return "advanced"

    # 检查 Pexels Key（存储在 glm_config.json 扩展字段或独立文件）
    pexels_config = Path(__file__).parent / "pexels_config.json"
    if pexels_config.exists():
        try:
            data = json.loads(pexels_config.read_text(encoding="utf-8"))
            if data.get("api_keys"):
                return "medium"
        except Exception:
            pass

    return "simple"


async def run_pipeline(
    text: str,
    title: str = "",
    mode: str = "auto",
    resolution: str = "1920x1080",
    stop_at: str = "video",
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> dict:
    """
    主 Pipeline 入口（AC29-32）。

    Args:
        text: 输入故事文本
        title: 视频标题
        mode: "auto" / "simple" / "medium" / "advanced"
        resolution: "1920x1080" / "1080x1920" / "1080x1080"
        stop_at: "storyboard" / "assets" / "video"
        progress_callback: fn(percent, message) 进度回调

    Returns:
        {state, progress, storyboard, video_path, error}
    """
    task_id = f"{mode}_{int(time.time())}"
    result = {
        "task_id": task_id,
        "state": STATE_PROCESSING,
        "progress": 0,
        "mode": mode,
        "storyboard": None,
        "video_path": None,
        "error": None,
    }

    def _progress(pct: int, msg: str):
        result["progress"] = pct
        if progress_callback:
            progress_callback(pct, msg)
        logger.info(f"[Pipeline] {pct}% — {msg}")

    try:
        # 自动检测模式
        if mode == "auto":
            mode = detect_mode()
            result["mode"] = mode
            logger.info(f"[Pipeline] 自动检测模式: {mode}")

        # 重置 Pexels 去重（新任务）
        from pexels_service import reset_session
        reset_session()

        _progress(5, "开始生成")

        # ════════ Stage 1: 导演分析 → 分镜 ════════
        _progress(10, "导演分析中...")
        storyboard = await _stage_1_director(text, title, mode)
        result["storyboard"] = asdict(storyboard)
        _progress(20, f"分镜完成: {len(storyboard.frames)} 帧")

        # 保存分镜 JSON（AC30 断点恢复）
        sb_path = OUTPUT_DIR / f"{task_id}_storyboard.json"
        sb_path.write_text(
            json.dumps(asdict(storyboard), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if stop_at == "storyboard":
            result["state"] = STATE_COMPLETE
            result["progress"] = 100
            return result

        # ════════ Stage 2: 资产生成 ════════
        if mode == "simple":
            # 简单模式跳过资产生成
            _progress(80, "简单模式，跳过资产生成")
        else:
            _progress(25, "资产生成中...")
            await _stage_2_assets(storyboard, mode, _progress)
            _progress(60, "资产生成完成")

        if stop_at == "assets":
            result["state"] = STATE_COMPLETE
            result["progress"] = 100
            result["storyboard"] = asdict(storyboard)
            return result

        # ════════ Stage 3-4: 渲染 + 合成 ════════
        if mode == "simple":
            # 简单模式沿用原有 HTML 生成
            _progress(90, "生成 HTML 动画...")
            from generator import generate_timeline, render_html
            timeline_data = await generate_timeline(text)
            html_content = render_html(title or text[:20], timeline_data)
            html_path = OUTPUT_DIR / f"{task_id}.html"
            html_path.write_text(html_content, encoding="utf-8")
            result["video_path"] = str(html_path)
        else:
            _progress(65, "视频合成中...")
            video_path = await _stage_3_4_compose(
                storyboard, task_id, resolution, _progress
            )
            result["video_path"] = video_path

        result["state"] = STATE_COMPLETE
        result["progress"] = 100
        _progress(100, "完成!")
        return result

    except Exception as e:
        logger.error(f"[Pipeline] 失败: {e}", exc_info=True)
        result["state"] = STATE_FAILED
        result["error"] = str(e)
        return result


# ─── Stage 实现 ──────────────────────────────────────────────

async def _stage_1_director(text: str, title: str, mode: str) -> Storyboard:
    """Stage 1: 导演 LLM 分析文本 → 生成分镜。用 DeepSeek（搜索词质量更好）。"""
    from generator import generate_timeline

    # DeepSeek 做导演（search_term 输出质量更好）
    timeline_data = await generate_timeline(text, use_glm=False)

    # 将现有 timeline 格式转换为 Storyboard
    storyboard = Storyboard(title=title or text[:20])

    # 提取角色（含性别）
    chars = timeline_data.get("chars", {})
    for name, info in chars.items():
        storyboard.characters.append(CharacterConfig(
            name=name,
            color=info.get("color", "#333"),
            gender=info.get("gender", ""),
        ))

    # 提取帧（限制最多 15 帧，防止文本过长导致几十帧）
    timeline = timeline_data.get("timeline", [])
    frame_events = [e for e in timeline if e.get("action") in ("dialogue", "narr")]
    if len(frame_events) > 15:
        frame_events = frame_events[:15]

    for i, event in enumerate(frame_events):
        frame = StoryboardFrame(
            index=i,
            narration=event.get("text", ""),
            speaker=event.get("who", "narrator") if event.get("action") == "dialogue" else "narrator",
            mood_tag=event.get("mood", "neutral"),
            image_prompt=event.get("scene_desc", ""),  # GLM-Image 用这个生成背景
        )
        # 存储 Pexels 搜索关键词（英文）
        frame.search_term = event.get("search_term", "")
        storyboard.frames.append(frame)

    return storyboard


async def _stage_2_assets(
    storyboard: Storyboard,
    mode: str,
    progress_fn: Callable,
):
    """Stage 2: 按帧并行生成资产（图/音/BGM）。"""
    total = len(storyboard.frames)

    for i, frame in enumerate(storyboard.frames):
        pct = 25 + int((i / max(total, 1)) * 35)
        progress_fn(pct, f"生成第 {i+1}/{total} 帧资产")

        # 每帧独立 try（AC35 帧级隔离）
        try:
            await _generate_frame_assets(frame, storyboard, mode)
        except Exception as e:
            logger.warning(f"[Stage2] 帧 {i} 资产生成失败: {e}")
            # 失败帧保持空路径，后续合成时降级处理


async def _generate_frame_assets(
    frame: StoryboardFrame,
    storyboard: Storyboard,
    mode: str,
):
    """为单帧生成所有资产。"""
    # 找到角色配置
    char_config = next(
        (c for c in storyboard.characters if c.name == frame.speaker),
        None,
    )
    gender = char_config.gender if char_config else ""

    # ── TTS 配音（中级模式直接用 Edge-TTS，稳定可靠）──
    from edge_tts_service import generate_speech as edge_speak
    frame.audio_path = await edge_speak(
        text=frame.narration,
        scene_index=frame.index,
        character_name=frame.speaker,
        gender=gender,
    )

    # ── 场景图/视频 ──
    if mode == "advanced" and frame.image_prompt:
        from glm_image import generate_scene_image
        frame.image_path = await generate_scene_image(
            prompt=frame.image_prompt,
            scene_index=frame.index,
        )

    if not frame.image_path and mode in ("medium", "advanced"):
        # Pexels 视频背景 — 使用英文搜索关键词
        pexels_config = Path(__file__).parent / "pexels_config.json"
        if pexels_config.exists():
            try:
                data = json.loads(pexels_config.read_text(encoding="utf-8"))
                keys = data.get("api_keys", [])
                if keys:
                    from pexels_service import search_and_download
                    # 优先用导演生成的 search_term，其次用 scene_desc 的前几个词
                    keyword = getattr(frame, "search_term", "") or frame.image_prompt or "nature"
                    # 确保是英文（Pexels 英文搜索效果远好于中文）
                    if keyword and any('\u4e00' <= c <= '\u9fff' for c in keyword):
                        keyword = frame.mood_tag or "nature scenery"
                    frame.image_path = await search_and_download(
                        keyword=keyword,
                        scene_index=frame.index,
                        api_keys=keys,
                    )
            except Exception as e:
                logger.warning(f"[Pexels] 帧 {frame.index}: {e}")

    # ── BGM 标签 ──
    frame.bgm_tag = frame.mood_tag


async def _stage_3_4_compose(
    storyboard: Storyboard,
    task_id: str,
    resolution: str,
    progress_fn: Callable,
) -> Optional[str]:
    """Stage 3-4: 快速合成（参考 MoneyPrinterPlus，每帧独立处理+concat copy）"""
    from video_compose import compose_fast, get_bgm_file

    # 获取每帧实际音频时长
    for frame in storyboard.frames:
        if frame.audio_path and Path(frame.audio_path).exists():
            frame.duration = _get_audio_duration(frame.audio_path)
        elif not frame.duration:
            frame.duration = 3.0

    progress_fn(65, "视频合成中...")

    # 构建帧数据（每帧 = 视频素材 + 配音 + 字幕文本）
    frame_data = []
    for frame in storyboard.frames:
        frame_data.append({
            "index": frame.index,
            "video_path": frame.image_path or "",  # Pexels 视频 or 图片
            "audio_path": frame.audio_path or "",
            "text": frame.narration,
            "duration": frame.duration,
        })

    # BGM
    mood = storyboard.frames[0].mood_tag if storyboard.frames else ""
    bgm_file = get_bgm_file(mood)

    # 快速合成
    w, h = [int(x) for x in resolution.split("x")]
    final_path = str(OUTPUT_DIR / f"{task_id}_final.mp4")

    progress_fn(70, f"处理 {len(frame_data)} 帧...")
    result = compose_fast(
        frames=frame_data,
        output_path=final_path,
        bgm_file=bgm_file,
        resolution=(w, h),
    )

    if result:
        progress_fn(95, "完成")
        storyboard.final_video = result
        storyboard.total_duration = sum(f.duration for f in storyboard.frames)
    else:
        progress_fn(95, "合成失败")

    return result


# ─── 辅助函数 ────────────────────────────────────────────────

def _get_audio_duration(path: str) -> float:
    """获取音频时长（秒）。"""
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=10,
        )
        # 从 stderr 中提取 Duration
        import re
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 3.0  # 默认 3 秒


def _concat_audio(files: list[str], output: str):
    """拼接多个音频文件。"""
    import tempfile, subprocess, shutil

    if not files:
        return
    if len(files) == 1:
        shutil.copy2(files[0], output)
        return

    # 用 ffmpeg concat
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for fp in files:
            abs_p = str(Path(fp).absolute()).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")
        list_file = f.name

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_file, "-c", "copy", output],
            capture_output=True, timeout=60,
        )
    finally:
        Path(list_file).unlink(missing_ok=True)


def _image_to_video(
    image: str, audio: str, output: str, bgm: Optional[str] = None
):
    """静态图片+音频→视频。"""
    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image,
        "-i", audio,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-pix_fmt", "yuv420p",
        output,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)


def _blank_video_with_audio(
    audio: str, output: str, bgm: Optional[str], resolution: str
):
    """黑底+音频→视频。"""
    import subprocess
    w, h = resolution.split("x")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d=999",
        "-i", audio,
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", "-pix_fmt", "yuv420p",
        output,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)
