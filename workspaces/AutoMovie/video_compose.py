"""
火柴人剧场 — 视频合成服务（参考 MoneyPrinterTurbo）
使用 moviepy 进行最终合成：视频 + 配音 + BGM + 字幕

核心方案直接搬自 MoneyPrinterTurbo generate_video()：
- AudioFileClip + MultiplyVolume 配音
- AudioFileClip + AudioLoop + AudioFadeOut BGM
- CompositeAudioClip 混合
- SubtitlesClip + TextClip 字幕
- video_clip.with_audio() 合并
"""

import os
import random
import shutil
import logging
from pathlib import Path
from typing import Optional

from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip,
    TextClip, CompositeVideoClip, CompositeAudioClip,
    ColorClip, concatenate_videoclips,
)
from moviepy.audio import fx as afx

logger = logging.getLogger(__name__)

BGM_DIR = Path(__file__).parent / "bgm"
FONTS_DIR = Path(__file__).parent / "fonts"
OUTPUT_DIR = Path(__file__).parent / "output"


def compose_video(
    video_segments: list[str],
    audio_file: str,
    output_path: str,
    bgm_file: Optional[str] = None,
    subtitle_items: Optional[list[tuple]] = None,
    bgm_volume: float = 0.2,
    voice_volume: float = 1.0,
    resolution: tuple[int, int] = (1920, 1080),
) -> Optional[str]:
    """
    最终视频合成（搬自 MoneyPrinterTurbo generate_video 核心逻辑）。

    Args:
        video_segments: 视频片段路径列表
        audio_file: 合并后的配音 mp3
        output_path: 输出 mp4 路径
        bgm_file: BGM 文件路径（可选）
        subtitle_items: 字幕列表 [(start_s, end_s, text), ...]
        bgm_volume: BGM 音量（0-1）
        voice_volume: 配音音量
        resolution: 输出分辨率 (w, h)

    Returns:
        输出路径，失败返回 None
    """
    video_width, video_height = resolution

    try:
        # Step 1: 拼接视频片段 → 一个完整视频
        logger.info(f"[Compose] 拼接 {len(video_segments)} 个视频片段...")
        clips = []
        for seg_path in video_segments:
            if not Path(seg_path).exists():
                continue
            clip = VideoFileClip(seg_path)
            # 统一分辨率
            if clip.size != [video_width, video_height]:
                clip = _resize_clip(clip, video_width, video_height)
            clips.append(clip)

        if not clips:
            logger.error("[Compose] 无有效视频片段")
            return None

        video_clip = concatenate_videoclips(clips, method="compose")
        logger.info(f"[Compose] 拼接完成: {video_clip.duration:.1f}s")

        # Step 2: 配音（参考 MoneyPrinterTurbo）
        audio_clip = AudioFileClip(audio_file)
        audio_clip = audio_clip.with_effects([afx.MultiplyVolume(voice_volume)])

        # Step 3: BGM（参考 MoneyPrinterTurbo）
        if bgm_file and Path(bgm_file).exists():
            try:
                bgm_clip = AudioFileClip(bgm_file)
                bgm_clip = bgm_clip.with_effects([
                    afx.MultiplyVolume(bgm_volume),
                    afx.AudioFadeOut(3),
                    afx.AudioLoop(duration=video_clip.duration),
                ])
                audio_clip = CompositeAudioClip([audio_clip, bgm_clip])
                logger.info(f"[Compose] BGM 已叠加 (vol={bgm_volume})")
            except Exception as e:
                logger.warning(f"[Compose] BGM 加载失败: {e}")

        # Step 4: 合并音视频
        video_clip = video_clip.with_audio(audio_clip)

        # Step 5: 字幕（如果有）
        if subtitle_items:
            text_clips = _create_subtitle_clips(
                subtitle_items, video_width, video_height
            )
            if text_clips:
                video_clip = CompositeVideoClip([video_clip, *text_clips])
                logger.info(f"[Compose] 字幕已叠加: {len(text_clips)} 条")

        # Step 6: 输出
        logger.info(f"[Compose] 写入文件: {output_path}")
        video_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="128k",
            fps=30,
            threads=2,
            logger=None,
        )

        # 清理
        video_clip.close()
        for clip in clips:
            clip.close()

        if Path(output_path).exists():
            size_mb = Path(output_path).stat().st_size / 1024 / 1024
            logger.info(f"[Compose] 完成: {size_mb:.1f}MB")
            return output_path
        return None

    except Exception as e:
        logger.error(f"[Compose] 合成失败: {e}", exc_info=True)
        return None


def _resize_clip(clip, target_w: int, target_h: int):
    """统一分辨率（letterbox 方式，参考 MoneyPrinterTurbo）"""
    clip_w, clip_h = clip.size
    clip_ratio = clip_w / clip_h
    target_ratio = target_w / target_h

    if abs(clip_ratio - target_ratio) < 0.01:
        return clip.resized(new_size=(target_w, target_h))

    # letterbox: 缩放后居中，黑边填充
    if clip_ratio > target_ratio:
        scale = target_w / clip_w
    else:
        scale = target_h / clip_h

    new_w = int(clip_w * scale)
    new_h = int(clip_h * scale)

    bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0)).with_duration(clip.duration)
    resized = clip.resized(new_size=(new_w, new_h)).with_position("center")
    return CompositeVideoClip([bg, resized])


def _create_subtitle_clips(
    items: list[tuple],
    video_width: int,
    video_height: int,
) -> list:
    """创建字幕 TextClip 列表"""
    font_path = str(FONTS_DIR / "MicrosoftYaHeiNormal.ttc")
    if not Path(font_path).exists():
        font_path = str(FONTS_DIR / "STHeitiMedium.ttc")
    if not Path(font_path).exists():
        return []

    text_clips = []
    for start_s, end_s, text in items:
        if not text.strip():
            continue
        try:
            txt_clip = TextClip(
                text=text.strip(),
                font=font_path,
                font_size=28,
                color="white",
                stroke_color="black",
                stroke_width=1,
                size=(int(video_width * 0.85), None),
                text_align="center",
            )
            txt_clip = txt_clip.with_start(start_s).with_end(end_s)
            txt_clip = txt_clip.with_position(("center", video_height * 0.88))
            text_clips.append(txt_clip)
        except Exception as e:
            logger.warning(f"[Subtitle] 字幕创建失败: {e}")
            continue

    return text_clips


def get_bgm_file(mood_tag: str = "") -> Optional[str]:
    """按氛围标签选择 BGM"""
    if not BGM_DIR.exists():
        return None
    files = list(BGM_DIR.glob("*.mp3"))
    if not files:
        return None

    # 尝试按标签匹配
    import json
    metadata_path = BGM_DIR / "metadata.json"
    if mood_tag and metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            tracks = meta.get("tracks", {})
            mood_map = meta.get("mood_mapping", {})
            target = mood_map.get(mood_tag, mood_tag)
            matched = [
                BGM_DIR / f for f, info in tracks.items()
                if info.get("mood") == target and (BGM_DIR / f).exists()
            ]
            if matched:
                return str(random.choice(matched))
        except Exception:
            pass

    return str(random.choice(files))
