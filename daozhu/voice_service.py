"""
岛主 DaoZhu — 语音交互服务（#085）
参考: RealtimeSTT_LLM_TTS + RealtimeVoiceChat

架构：
- 前端 Web Audio API 录音 → WebSocket 发送 PCM 音频块
- 后端接收音频 → RealtimeSTT 转文字 → agent 处理 → Edge-TTS 生成语音 → 回传
- 支持唤醒词"岛主"（openwakeword）

依赖：
- pip install realtimestt[openwakeword] realtimetts[edge]
"""

import asyncio
import json
import logging
import time
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 全局状态
_recorder = None
_recorder_ready = threading.Event()
_is_listening = False


def check_voice_available() -> dict:
    """检查语音功能依赖是否可用"""
    status = {"stt": False, "tts": False, "wakeword": False}

    try:
        import RealtimeSTT
        status["stt"] = True
    except ImportError:
        pass

    try:
        import edge_tts
        status["tts"] = True
    except ImportError:
        pass

    try:
        from openwakeword import Model
        status["wakeword"] = True
    except ImportError:
        pass

    return status


async def speech_to_text_from_audio(audio_bytes: bytes, sample_rate: int = 16000) -> Optional[str]:
    """
    将音频字节转为文字（简单版，直接用 Whisper）。
    用于前端录音后一次性发送的场景（按住说话模式）。
    """
    try:
        import tempfile
        import wave

        # 保存为临时 WAV 文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            with wave.open(f, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)

        # 用 faster-whisper 转录
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(tmp_path, language="zh")
        text = " ".join(seg.text for seg in segments).strip()

        # 清理临时文件
        Path(tmp_path).unlink(missing_ok=True)

        if text:
            logger.info(f"[Voice STT] 识别结果: {text}")
        return text or None

    except ImportError:
        logger.warning("[Voice] faster-whisper 未安装")
        return None
    except Exception as e:
        logger.error(f"[Voice STT] 失败: {e}")
        return None


async def text_to_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> Optional[bytes]:
    """
    文字转语音（返回 mp3 字节）。
    复用 Edge-TTS。
    """
    try:
        import edge_tts
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp_path)

        audio_bytes = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)

        if len(audio_bytes) > 500:
            logger.info(f"[Voice TTS] 生成语音: {len(audio_bytes)//1024}KB")
            return audio_bytes
        return None

    except Exception as e:
        logger.error(f"[Voice TTS] 失败: {e}")
        return None
