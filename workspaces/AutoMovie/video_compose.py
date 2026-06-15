"""
火柴人剧场 — 视频合成服务（参考 MoneyPrinterPlus）
方案：每帧独立处理 → ffmpeg concat copy（极快）

MoneyPrinterPlus 思路：
1. normalize_video: 每帧统一分辨率+帧率（ffmpeg scale+crop）
2. 每帧内嵌字幕（ffmpeg drawtext/subtitles）
3. 每帧混入配音（ffmpeg -i video -i audio -shortest）
4. concat copy 拼接（-c copy，秒级完成）
5. 最后叠加 BGM

不用 moviepy 做整体合成 → 避免重编码 → 速度快 10 倍
"""

import json
import logging
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BGM_DIR = Path(__file__).parent / "bgm"
FONTS_DIR = Path(__file__).parent / "fonts"
OUTPUT_DIR = Path(__file__).parent / "output"


def compose_fast(
    frames: list[dict],
    output_path: str,
    bgm_file: Optional[str] = None,
    bgm_volume: float = 0.2,
    resolution: tuple[int, int] = (1920, 1080),
    fps: int = 30,
) -> Optional[str]:
    """
    快速视频合成（参考 MoneyPrinterPlus）。

    Args:
        frames: [{video_path, audio_path, text, duration}, ...]
        output_path: 最终输出路径
        bgm_file: BGM 路径
        bgm_volume: BGM 音量
        resolution: (width, height)
        fps: 帧率

    Returns:
        输出路径，失败返回 None
    """
    w, h = resolution

    if not shutil.which("ffmpeg"):
        logger.error("[Compose] ffmpeg 未安装")
        return None

    # Step 1: 每帧独立处理（视频+音频+字幕 → 一个完整片段）
    logger.info(f"[Compose] 处理 {len(frames)} 帧...")
    processed = []

    for i, frame in enumerate(frames):
        seg_path = str(OUTPUT_DIR / f"_seg_{i:03d}.mp4")
        ok = _process_single_frame(frame, seg_path, w, h, fps)
        if ok:
            processed.append(seg_path)

    if not processed:
        logger.error("[Compose] 无可用片段")
        return None

    logger.info(f"[Compose] {len(processed)} 帧处理完成")

    # Step 2: concat copy 拼接（秒级）
    concat_path = str(OUTPUT_DIR / "_concat.mp4")
    if not _concat_copy(processed, concat_path):
        return None

    # Step 3: 叠加 BGM
    if bgm_file and Path(bgm_file).exists():
        final = _add_bgm(concat_path, bgm_file, output_path, bgm_volume)
    else:
        shutil.move(concat_path, output_path)
        final = output_path

    # 清理临时文件
    for p in processed:
        Path(p).unlink(missing_ok=True)
    Path(concat_path).unlink(missing_ok=True)

    if final and Path(final).exists():
        size_mb = Path(final).stat().st_size / 1024 / 1024
        logger.info(f"[Compose] 完成: {size_mb:.1f}MB")
        return final
    return None


def _process_single_frame(
    frame: dict, output: str, w: int, h: int, fps: int
) -> bool:
    """
    处理单帧：视频素材 + 配音 + 字幕 → 一个完整 mp4 片段。
    参考 MoneyPrinterPlus normalize_video + generate_subtitles
    """
    video_path = frame.get("video_path", "")
    audio_path = frame.get("audio_path", "")
    text = frame.get("text", "")
    duration = frame.get("duration", 3.0)

    # 无视频素材 → 黑底
    if not video_path or not Path(video_path).exists():
        video_input = ["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={fps}:d={duration:.2f}"]
    elif video_path.endswith(".mp4"):
        # 视频素材 → 裁剪到 duration + 统一分辨率
        video_input = ["-i", video_path, "-t", f"{duration:.2f}"]
    else:
        # 图片 → 循环
        video_input = ["-loop", "1", "-i", video_path, "-t", f"{duration:.2f}"]

    # 构建 ffmpeg 命令
    cmd = ["ffmpeg", "-y"] + video_input

    # 音频
    if audio_path and Path(audio_path).exists():
        cmd += ["-i", audio_path]
        audio_map = ["-map", "0:v", "-map", "1:a", "-shortest"]
    else:
        audio_map = ["-map", "0:v", "-an"]

    # 视频滤镜：统一分辨率 + 字幕
    vf_parts = [
        f"scale={w}:{h}:force_original_aspect_ratio=decrease",
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
        f"fps={fps}",
    ]

    # 字幕（drawtext，不需要 srt 文件）
    if text:
        # 转义单引号和特殊字符
        safe_text = text.replace("'", "'\\''").replace(":", "\\:").replace("%", "%%")
        font_path = str(FONTS_DIR / "MicrosoftYaHeiNormal.ttc").replace("\\", "/").replace(":", "\\:")
        vf_parts.append(
            f"drawtext=text='{safe_text}'"
            f":fontfile='{font_path}'"
            f":fontsize=42:fontcolor=white"
            f":borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y=h*0.82"
        )

    cmd += ["-vf", ",".join(vf_parts)]
    cmd += audio_map
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]

    if audio_path and Path(audio_path).exists():
        cmd += ["-c:a", "aac", "-b:a", "128k"]

    cmd += [output]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30, encoding="utf-8", errors="replace")
        if result.returncode == 0 and Path(output).exists():
            return True
        else:
            logger.warning(f"[Frame {frame.get('index',0)}] 处理失败: {result.stderr[:150] if result.stderr else ''}")
            return False
    except Exception as e:
        logger.warning(f"[Frame] 异常: {e}")
        return False


def _concat_copy(segments: list[str], output: str) -> bool:
    """
    ffmpeg concat demuxer 拼接（-c copy，秒级完成）。
    参考 MoneyPrinterPlus generate_video_with_bg_music
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for seg in segments:
            abs_p = str(Path(seg).absolute()).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")
        list_file = f.name

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            "-fflags", "+genpts",
            output,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and Path(output).exists():
            logger.info(f"[Concat] {len(segments)} 段拼接完成（copy模式）")
            return True
        logger.error(f"[Concat] 失败: {result.stderr.decode()[:150]}")
        return False
    finally:
        Path(list_file).unlink(missing_ok=True)


def _add_bgm(video: str, bgm: str, output: str, volume: float) -> Optional[str]:
    """叠加 BGM（循环 + 淡出 + 混音）"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-stream_loop", "-1", "-i", bgm,
        "-filter_complex",
        f"[1:a]volume={volume},afade=t=out:st=999:d=3[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0 and Path(output).exists():
            logger.info("[BGM] 叠加完成")
            return output
        logger.warning(f"[BGM] 失败，使用无BGM版本: {result.stderr.decode()[:100]}")
        shutil.copy2(video, output)
        return output
    except Exception:
        shutil.copy2(video, output)
        return output


def get_bgm_file(mood_tag: str = "") -> Optional[str]:
    """按氛围标签选择 BGM"""
    if not BGM_DIR.exists():
        return None
    files = list(BGM_DIR.glob("*.mp3"))
    if not files:
        return None

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
