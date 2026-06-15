"""
火柴人剧场 — 视频合成服务（#083 Stage 4）
使用 ffmpeg 合成：逐帧视频片段 + 配音 + BGM + 字幕 → 最终 MP4

参考: MoneyPrinterTurbo app/services/video.py
      Pixelle-Video pixelle_video/services/video.py

特点:
- concat demuxer 拼接（快速，无重编码）
- BGM ducking（配音时自动压低）
- 字幕硬编码（drawtext filter）
- 编码器回退（h264_nvenc → libx264）
"""

import logging
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"
BGM_DIR = Path(__file__).parent / "bgm"
FONTS_DIR = Path(__file__).parent / "fonts"


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用（AC25）。"""
    return shutil.which("ffmpeg") is not None


def get_bgm_file(mood_tag: str = "") -> Optional[str]:
    """
    按氛围标签选择 BGM（AC18/AC19）。
    使用 metadata.json 做标签匹配，无匹配时随机。
    """
    if not BGM_DIR.exists():
        return None
    files = list(BGM_DIR.glob("*.mp3"))
    if not files:
        return None

    # 尝试按标签匹配
    metadata_path = BGM_DIR / "metadata.json"
    if mood_tag and metadata_path.exists():
        try:
            import json
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            tracks = meta.get("tracks", {})
            mood_map = meta.get("mood_mapping", {})

            # 标准化 mood_tag
            target_mood = mood_map.get(mood_tag, mood_tag)

            # 筛选匹配的曲目
            matched = [
                BGM_DIR / fname
                for fname, info in tracks.items()
                if info.get("mood") == target_mood and (BGM_DIR / fname).exists()
            ]
            if matched:
                return str(random.choice(matched))
        except Exception:
            pass

    # 无匹配或无元数据 → 随机
    return str(random.choice(files))


def concat_segments(
    segments: list[str],
    output_path: str,
) -> Optional[str]:
    """
    拼接视频片段（AC25 concat demuxer，快速无重编码）。

    Args:
        segments: 视频片段文件路径列表
        output_path: 输出文件路径

    Returns:
        输出路径，失败返回 None
    """
    if not check_ffmpeg():
        logger.error("[Video] ffmpeg 未安装。安装: https://ffmpeg.org/download.html")
        return None

    if not segments:
        return None

    if len(segments) == 1:
        shutil.copy2(segments[0], output_path)
        return output_path

    # 创建 concat 列表文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for seg in segments:
            abs_path = str(Path(seg).absolute()).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
        concat_file = f.name

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                output_path,
            ],
            capture_output=True,
            timeout=120,
        )
        if result.returncode == 0 and Path(output_path).exists():
            logger.info(f"[Video] 拼接完成: {len(segments)} 段 → {output_path}")
            return output_path
        else:
            logger.error(f"[Video] 拼接失败: {result.stderr.decode()[:200]}")
            return None
    finally:
        os.unlink(concat_file)


def add_audio_and_bgm(
    video_path: str,
    audio_path: Optional[str],
    bgm_path: Optional[str],
    output_path: str,
    bgm_volume: float = 0.15,
) -> Optional[str]:
    """
    混合视频 + 配音 + BGM（AC20 ducking + AC21 循环+淡出）。
    使用简单可靠的 ffmpeg 命令，避免复杂 filter_complex。
    """
    if not check_ffmpeg():
        return None

    import subprocess

    # 策略：分步合成（更可靠）
    # Step 1: 视频 + 配音
    if audio_path and Path(audio_path).exists():
        temp_with_voice = output_path.replace(".mp4", "_voice.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            temp_with_voice,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"[Video] 配音合并失败: {result.stderr.decode()[:200]}")
            # 降级：无音频直接复制
            import shutil
            shutil.copy2(video_path, output_path)
            return output_path
        current_video = temp_with_voice
    else:
        current_video = video_path

    # Step 2: 叠加 BGM（如果有）
    if bgm_path and Path(bgm_path).exists():
        cmd = [
            "ffmpeg", "-y",
            "-i", current_video,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={bgm_volume},afade=t=out:st=999:d=3[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            logger.warning(f"[Video] BGM 叠加失败，使用无BGM版本: {result.stderr.decode()[:100]}")
            # BGM 失败不致命，用只有配音的版本
            import shutil
            shutil.copy2(current_video, output_path)
        # 清理临时文件
        if current_video != video_path and Path(current_video).exists():
            Path(current_video).unlink(missing_ok=True)
    else:
        # 没有 BGM，直接用当前视频
        if current_video != video_path:
            import shutil
            shutil.move(current_video, output_path)
        else:
            import shutil
            shutil.copy2(current_video, output_path)

    if Path(output_path).exists():
        logger.info(f"[Video] 音频混合完成: {output_path}")
        return output_path
    return None


def burn_subtitles(
    video_path: str,
    subtitles: list[dict],
    output_path: str,
    font_name: str = "MicrosoftYaHeiNormal.ttc",
    font_size: int = 24,
) -> Optional[str]:
    """
    硬编码字幕到视频（AC22/AC23）。

    Args:
        video_path: 输入视频
        subtitles: [{start_ms, end_ms, text}]
        output_path: 输出路径
        font_name: 字体文件名
        font_size: 字号

    Returns:
        输出路径，失败返回输入路径（字幕失败不阻塞）
    """
    if not subtitles or not check_ffmpeg():
        return video_path

    font_path = FONTS_DIR / font_name
    if not font_path.exists():
        logger.warning(f"[Video] 字体不存在: {font_path}")
        return video_path

    # 生成 SRT 字幕文件
    srt_path = Path(output_path).with_suffix(".srt")
    _write_srt(subtitles, str(srt_path))

    # ffmpeg 烧录字幕
    font_path_escaped = str(font_path).replace("\\", "/").replace(":", "\\:")
    srt_path_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", (
            f"subtitles='{srt_path_escaped}'"
            f":force_style='FontName=Microsoft YaHei,"
            f"FontSize={font_size},PrimaryColour=&HFFFFFF,"
            f"BackColour=&H80000000,BorderStyle=4,Outline=0,"
            f"Shadow=0,MarginV=30'"
        ),
        "-c:a", "copy",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0 and Path(output_path).exists():
            logger.info(f"[Video] 字幕烧录完成: {output_path}")
            # 清理临时 SRT
            srt_path.unlink(missing_ok=True)
            return output_path
        else:
            logger.warning(f"[Video] 字幕烧录失败，返回无字幕版本")
            srt_path.unlink(missing_ok=True)
            return video_path
    except Exception as e:
        logger.warning(f"[Video] 字幕异常: {e}")
        srt_path.unlink(missing_ok=True)
        return video_path


def _write_srt(subtitles: list[dict], path: str):
    """将字幕列表写为 SRT 格式。"""
    lines = []
    for i, sub in enumerate(subtitles, 1):
        start = _ms_to_srt_time(sub["start_ms"])
        end = _ms_to_srt_time(sub["end_ms"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(sub["text"])
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _ms_to_srt_time(ms: int) -> str:
    """毫秒转 SRT 时间格式 (HH:MM:SS,mmm)。"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms_rem = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_rem:03d}"


def _get_video_codec() -> str:
    """检测可用编码器（AC27 优先 GPU 加速）。"""
    # 尝试 NVIDIA GPU 编码器
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5,
        )
        if "h264_nvenc" in result.stdout:
            return "h264_nvenc"
    except Exception:
        pass
    return "libx264"
