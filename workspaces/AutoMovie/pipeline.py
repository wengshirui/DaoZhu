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

    if mode in ("medium", "advanced"):
        # 视频模式：用专门的视频分镜 prompt（参考 MoneyPrinterTurbo）
        return await _generate_video_storyboard(text, title)
    else:
        # 简单模式：用原有的火柴人动画导演
        from generator import generate_timeline
        timeline_data = await generate_timeline(text, use_glm=False)
        return _timeline_to_storyboard(timeline_data, title)


async def _generate_video_storyboard(text: str, title: str) -> Storyboard:
    """
    视频分镜生成器（参考 MoneyPrinterTurbo generate_script + generate_terms）。
    专注于：把文本拆成 8-12 个旁白段落 + 为每段生成视频搜索词。
    """
    from daozhu.config_db import get_secret
    from daozhu.config import get_config_value

    api_key = get_secret("DEEPSEEK_API_KEY")
    base_url = get_config_value("ai.base_url", "https://api.deepseek.com/v1")
    model = get_config_value("ai.model", "deepseek-chat")

    prompt = f"""你是一个短视频分镜脚本编写器。将用户输入的文本拆分为 8-12 个旁白段落，并为每段配上视频搜索关键词。

## 规则
1. 每段旁白 30-80 字，一句完整的话，适合 TTS 朗读
2. 每段必须有 search_term（2-4 个英文单词），用于搜索配图视频
3. search_term 必须是 Pexels 能搜到的通用场景，不要用专有名词（人名/公司名）
4. 相邻段的 search_term 有视觉连贯性（不要跳跃太大）
5. 最后一段是总结/提问/互动（收束感）
6. search_term 最后一段用收束画面（如 "conclusion question mark" 或 "thinking audience"）
7. 用中文旁白，search_term 用英文

## 好的 search_term 示例
- "breaking news studio broadcast"（新闻类）
- "technology office computer screen"（科技类）
- "stock market trading screen"（财经类）
- "person worried phone privacy"（隐私类）
- "document signing agreement"（协议类）

## 输出格式（纯 JSON，不要 markdown）
{{"segments": [{{"narration": "旁白文字", "search_term": "english search words", "speaker": "narrator"}}]}}

## 用户文本
{text[:2000]}"""

    messages = [{"role": "user", "content": prompt}]

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": messages, "max_tokens": 4000, "temperature": 0.3},
            )

        if resp.status_code != 200:
            raise RuntimeError(f"API 错误: {resp.status_code}")

        content = resp.json()["choices"][0]["message"]["content"]
        data = _parse_video_json(content)

        segments = data.get("segments", [])
        if not segments:
            raise RuntimeError("导演未生成分镜")

        # 构建 Storyboard
        storyboard = Storyboard(title=title)
        for i, seg in enumerate(segments[:15]):
            frame = StoryboardFrame(
                index=i,
                narration=seg.get("narration", ""),
                speaker=seg.get("speaker", "narrator"),
                mood_tag="neutral",
                image_prompt="",
            )
            frame.search_term = seg.get("search_term", "")
            storyboard.frames.append(frame)

        logger.info(f"[Director] 视频分镜: {len(storyboard.frames)} 帧")
        return storyboard

    except Exception as e:
        logger.error(f"[Director] 视频分镜失败: {e}")
        # 降级：简单按段落分
        return _fallback_split(text, title)


def _parse_video_json(content: str) -> dict:
    """解析 LLM 输出的 JSON"""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r'^```[a-zA-Z]*\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _fallback_split(text: str, title: str) -> Storyboard:
    """降级：按句号分段"""
    storyboard = Storyboard(title=title)
    sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip() and len(s.strip()) > 10]
    for i, sent in enumerate(sentences[:12]):
        frame = StoryboardFrame(
            index=i,
            narration=sent,
            speaker="narrator",
        )
        frame.search_term = "news broadcast studio"
        storyboard.frames.append(frame)
    return storyboard


def _timeline_to_storyboard(timeline_data: dict, title: str) -> Storyboard:
    """将火柴人 timeline 转为 Storyboard（简单模式用）"""
    storyboard = Storyboard(title=title)

    chars = timeline_data.get("chars", {})
    for name, info in chars.items():
        storyboard.characters.append(CharacterConfig(
            name=name,
            color=info.get("color", "#333"),
            gender=info.get("gender", ""),
        ))

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
            image_prompt=event.get("scene_desc", ""),
        )
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
