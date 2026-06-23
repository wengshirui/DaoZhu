"""
岛主 DaoZhu — 语音交互服务（#085）
参考: RealtimeSTT_LLM_TTS + RealtimeVoiceChat

配置项（config.json → voice 字段）：
- voice.wake_word: 唤醒词（默认"岛主"）
- voice.stt_engine: "whisper" / "glm"（默认 whisper）
- voice.stt_model: whisper 模型大小（tiny/base/small）
- voice.tts_engine: "edge" / "glm"（默认 edge）
- voice.tts_voice: 音色名称（默认 zh-CN-XiaoxiaoNeural）
- voice.enabled: 是否启用语音（默认 true）
"""

import asyncio
import json
import logging
import time
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_VOICE_CONFIG = {
    "enabled": True,
    "wake_word": "岛主",
    "stt_engine": "whisper",    # whisper / glm
    "stt_model": "base",        # tiny / base / small
    "tts_engine": "edge",       # edge / glm
    "tts_voice": "zh-CN-XiaoxiaoNeural",
}

# Edge-TTS 可用音色列表
EDGE_VOICES = {
    "晓晓（温柔女声）": "zh-CN-XiaoxiaoNeural",
    "云希（年轻男声）": "zh-CN-YunxiNeural",
    "云健（成熟男声）": "zh-CN-YunjianNeural",
    "晓秋（知性女声）": "zh-CN-XiaoqiuNeural",
    "晓忆（活泼女声）": "zh-CN-XiaoyiNeural",
    "云扬（播音男声）": "zh-CN-YunyangNeural",
}


def get_voice_config() -> dict:
    """获取语音配置"""
    from .config import get_config_value
    config = {}
    for key, default in DEFAULT_VOICE_CONFIG.items():
        config[key] = get_config_value(f"voice.{key}", default)
    return config


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


async def text_to_speech(text: str, voice: str = "") -> Optional[bytes]:
    """
    文字转语音（返回 mp3 字节）。
    根据配置选择 Edge-TTS 或 GLM-TTS。
    """
    config = get_voice_config()
    if not voice:
        voice = config["tts_voice"]
    engine = config["tts_engine"]

    if engine == "glm":
        return await _tts_glm(text, voice)
    else:
        return await _tts_edge(text, voice)


async def _tts_edge(text: str, voice: str) -> Optional[bytes]:
    """Edge-TTS 实现"""
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
            logger.info(f"[Voice TTS] Edge 生成: {len(audio_bytes)//1024}KB")
            return audio_bytes
        return None
    except Exception as e:
        logger.error(f"[Voice TTS] Edge 失败: {e}")
        return None


async def _tts_glm(text: str, voice: str) -> Optional[bytes]:
    """GLM-TTS 实现（云端高质量）"""
    try:
        from .config import get_config_value
        import httpx

        api_key = get_config_value("voice.glm_api_key", "")
        if not api_key:
            # 降级到 Edge
            logger.info("[Voice TTS] GLM Key 未配置，降级 Edge")
            return await _tts_edge(text, "zh-CN-XiaoxiaoNeural")

        base_url = "https://open.bigmodel.cn/api/paas/v4"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/audio/speech",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "glm-tts", "input": text, "voice": voice or "alloy"},
            )
            if resp.status_code == 200 and len(resp.content) > 500:
                logger.info(f"[Voice TTS] GLM 生成: {len(resp.content)//1024}KB")
                return resp.content
            else:
                logger.warning(f"[Voice TTS] GLM 返回 {resp.status_code}，降级 Edge")
                return await _tts_edge(text, "zh-CN-XiaoxiaoNeural")
    except Exception as e:
        logger.error(f"[Voice TTS] GLM 失败: {e}")
        return await _tts_edge(text, "zh-CN-XiaoxiaoNeural")
