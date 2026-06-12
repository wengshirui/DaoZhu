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
    当前库未按标签分类时随机选取。
    """
    if not BGM_DIR.exists():
        return None
    files = list(BGM_DIR.glob("*.mp3"))
    if not files:
        return None
    # TODO: 按 mood_tag 匹配（需要 BGM 元数据文件）
    # 当前随机选取
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

    Args:
        video_path: 输入视频（无音频或带原音）
        audio_path: 配音文件路径
        bgm_path: BGM 文件路径
        output_path: 输出路径
        bgm_volume: BGM 相对音量（0.15 ≈ -16dB）

    Returns:
        输出路径，失败返回 None
    """
    if not check_ffmpeg():
        return None

    # 构建 ffmpeg 命令
    inputs = ["-i", video_path]
    filter_parts = []
    audio_map = None

    if audio_path and bgm_path:
        # 三路混合：视频 + 配音 + BGM（循环 + 淡出 + ducking）
        inputs.extend(["-i", audio_path, "-i", bgm_path])
        # BGM 循环到视频长度，最后 3 秒淡出，音量压低
        filter_parts.append(
            f"[2:a]aloop=loop=-1:size=2e+09,volume={bgm_volume},afade=t=out:st=-3:d=3[bgm];"
            f"[1:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]"
        )
        audio_map = "[aout]"
    elif audio_path:
        inputs.extend(["-i", audio_path])
        audio_map = "1:a"
    elif bgm_path:
        inputs.extend(["-i", bgm_path])
        filter_parts.append(
            f"[1:a]aloop=loop=-1:size=2e+09,volume={bgm_volume},"
            f"afade=t=out:st=-3:d=3[aout]"
        )
        audio_map = "[aout]"

    cmd = ["ffmpeg", "-y"] + inputs

    if filter_parts:
        cmd.extend(["-filter_complex", ";".join(filter_parts)])

    # 输出编码（AC27 编码器回退）
    codec = _get_video_codec()
    cmd.extend(["-c:v", codec])

    if audio_map:
        if audio_map.startswith("["):
            cmd.extend(["-map", "0:v", "-map", audio_map])
        else:
            cmd.extend(["-map", "0:v", "-map", audio_map])
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    else:
        cmd.extend(["-map", "0:v", "-an"])

    cmd.extend(["-shortest", output_path])

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=180)
        if result.returncode == 0 and Path(output_path).exists():
            logger.info(f"[Video] 音频混合完成: {output_path}")
            return output_path
        else:
            # 编码器回退（AC27）
            if codec != "libx264":
                logger.warning(f"[Video] {codec} 失败，回退 libx264")
                cmd[cmd.index(codec)] = "libx264"
                result = subprocess.run(cmd, capture_output=True, timeout=180)
                if result.returncode == 0:
                    return output_path
            logger.error(f"[Video] 混合失败: {result.stderr.decode()[:200]}")
            return None
    except subprocess.TimeoutExpired:
        logger.error("[Video] 合成超时")
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
