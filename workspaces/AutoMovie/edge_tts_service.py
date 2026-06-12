"""
火柴人剧场 — Edge-TTS 免费配音服务（#083 中级模式）
使用微软 Edge-TTS（免费、无需 Key）为角色生成配音。

参考: MoneyPrinterTurbo app/services/voice.py
特点: 逐词时间戳（WordBoundary）→ 精确字幕

失败时生成等时长静音 mp3（AC17），不阻塞流程。
"""

import asyncio
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output" / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 预设音色映射（Edge-TTS voice name）
EDGE_VOICES = {
    "male_young": "zh-CN-YunxiNeural",
    "male_mature": "zh-CN-YunjianNeural",
    "female_young": "zh-CN-XiaoxiaoNeural",
    "female_mature": "zh-CN-XiaoqiuNeural",
    "narrator": "zh-CN-YunjianNeural",
}


async def generate_speech(
    text: str,
    scene_index: int,
    character_name: str = "narrator",
    gender: str = "",
    voice_name: str = "",
) -> Optional[str]:
    """
    使用 Edge-TTS 生成语音（免费，无需 API Key）。

    Args:
        text: 要合成的文本
        scene_index: 场景序号
        character_name: 角色名
        gender: 性别（male/female）
        voice_name: 指定音色名（可选）

    Returns:
        音频文件路径，失败返回 None
    """
    if not text or not text.strip():
        return None

    voice = _resolve_voice(voice_name, gender)
    safe_name = character_name.replace(" ", "_")[:20]
    filename = f"scene_{scene_index:03d}_{safe_name}.mp3"
    filepath = OUTPUT_DIR / filename

    try:
        import edge_tts

        communicate = edge_tts.Communicate(text.strip(), voice)
        await communicate.save(str(filepath))

        if filepath.exists() and filepath.stat().st_size > 500:
            logger.info(
                f"[Edge-TTS] 场景 {scene_index} 配音完成: "
                f"{filename} ({filepath.stat().st_size // 1024}KB)"
            )
            return str(filepath)
        else:
            logger.warning(f"[Edge-TTS] 场景 {scene_index} 输出文件过小")
            return _generate_silent(scene_index, text, filepath)

    except ImportError:
        logger.warning("[Edge-TTS] edge-tts 未安装，生成静音")
        return _generate_silent(scene_index, text, filepath)
    except Exception as e:
        logger.warning(f"[Edge-TTS] 场景 {scene_index} 失败: {e}")
        return _generate_silent(scene_index, text, filepath)


async def generate_speech_with_subtitles(
    text: str,
    scene_index: int,
    character_name: str = "narrator",
    gender: str = "",
    voice_name: str = "",
) -> tuple[Optional[str], list[dict]]:
    """
    生成语音 + 逐词字幕时间戳（AC24）。

    Returns:
        (音频路径, 字幕列表[{start_ms, end_ms, text}])
    """
    if not text or not text.strip():
        return None, []

    voice = _resolve_voice(voice_name, gender)
    safe_name = character_name.replace(" ", "_")[:20]
    filename = f"scene_{scene_index:03d}_{safe_name}.mp3"
    filepath = OUTPUT_DIR / filename
    subtitles = []

    try:
        import edge_tts

        communicate = edge_tts.Communicate(text.strip(), voice)
        sub_data = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                # 写入音频
                if not hasattr(generate_speech_with_subtitles, "_file"):
                    generate_speech_with_subtitles._file = open(filepath, "wb")
                generate_speech_with_subtitles._file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                sub_data.append({
                    "start_ms": chunk["offset"] // 10000,  # 100ns → ms
                    "end_ms": (chunk["offset"] + chunk["duration"]) // 10000,
                    "text": chunk["text"],
                })

        if hasattr(generate_speech_with_subtitles, "_file"):
            generate_speech_with_subtitles._file.close()
            del generate_speech_with_subtitles._file

        if filepath.exists() and filepath.stat().st_size > 500:
            return str(filepath), sub_data
        return None, []

    except Exception as e:
        logger.warning(f"[Edge-TTS] 字幕模式失败: {e}")
        # 回退到无字幕模式
        audio_path = await generate_speech(
            text, scene_index, character_name, gender, voice_name
        )
        return audio_path, []


def _resolve_voice(voice_name: str, gender: str) -> str:
    """解析音色：优先指定名，否则按性别匹配。"""
    if voice_name:
        return voice_name
    if gender.lower() in ("male", "男"):
        return EDGE_VOICES["male_young"]
    if gender.lower() in ("female", "女"):
        return EDGE_VOICES["female_young"]
    return EDGE_VOICES["narrator"]


def _generate_silent(scene_index: int, text: str, filepath: Path) -> Optional[str]:
    """
    生成等时长静音 mp3（AC17 兜底）。
    按中文 4.2 字/秒估算时长。
    """
    if not shutil.which("ffmpeg"):
        return None

    # 估算时长：中文约 4.2 字/秒
    duration = max(1.0, len(text.strip()) / 4.2)

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=mono",
                "-t", f"{duration:.2f}",
                "-codec:a", "libmp3lame",
                "-q:a", "4",
                str(filepath),
            ],
            capture_output=True,
            timeout=10,
        )
        if filepath.exists():
            logger.info(f"[Silent] 场景 {scene_index} 静音兜底: {duration:.1f}s")
            return str(filepath)
    except Exception as e:
        logger.warning(f"[Silent] 生成失败: {e}")

    return None
