"""
火柴人剧场 — GLM-TTS 角色配音服务
调用智谱 GLM-TTS API 为角色对话生成语音。

支持：
- 零样本声色克隆（通过角色声色参数控制）
- 多角色独立音色
- 旁白使用默认中性音色

失败时该段静音处理（AC10），不阻塞流程。
参考: Pixelle-Video services/tts_service.py
"""

import logging
from pathlib import Path
from typing import Optional

import httpx

from glm_config import load_config

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output" / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 预设音色（智谱 GLM-TTS 平台音色）
# 参考 https://open.bigmodel.cn/dev/api/speech/tts
VOICE_PRESETS = {
    "male_young": "alloy",
    "male_mature": "echo",
    "female_young": "nova",
    "female_mature": "shimmer",
    "narrator": "onyx",
}


async def generate_speech(
    text: str,
    scene_index: int,
    character_name: str = "narrator",
    voice_id: str = "",
    gender: str = "",
) -> Optional[str]:
    """
    调用 GLM-TTS 生成语音。

    Args:
        text: 要合成的文本（对话内容或旁白）
        scene_index: 场景序号
        character_name: 角色名（用于文件命名）
        voice_id: 指定音色 ID（导演配置）
        gender: 角色性别（male/female），用于自动匹配音色

    Returns:
        生成的音频文件路径，失败返回 None（AC10 静音降级）
    """
    config = load_config()
    if not config.api_key:
        return None

    if not text or not text.strip():
        return None

    # 确定音色
    final_voice = _resolve_voice(voice_id, gender)

    try:
        payload = {
            "model": config.tts_model,
            "input": text.strip(),
            "voice": final_voice,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{config.base_url}/audio/speech",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"[GLM-TTS] API 返回 {resp.status_code}: "
                    f"{resp.text[:200]}"
                )
                return None

            # API 直接返回音频二进制流
            audio_data = resp.content
            if not audio_data or len(audio_data) < 1000:
                logger.warning("[GLM-TTS] 返回音频数据过小")
                return None

            # 保存音频文件
            safe_name = character_name.replace(" ", "_")[:20]
            filename = f"scene_{scene_index:03d}_{safe_name}.mp3"
            filepath = OUTPUT_DIR / filename
            filepath.write_bytes(audio_data)

            logger.info(
                f"[GLM-TTS] 场景 {scene_index} 配音完成: "
                f"{filename} ({len(audio_data)//1024}KB)"
            )
            return str(filepath)

    except httpx.TimeoutException:
        logger.warning(f"[GLM-TTS] 场景 {scene_index} 超时")
        return None
    except Exception as e:
        logger.warning(f"[GLM-TTS] 场景 {scene_index} 失败: {e}")
        return None


def _resolve_voice(voice_id: str, gender: str) -> str:
    """解析音色：优先用指定 ID，否则按性别匹配预设。"""
    if voice_id:
        return voice_id
    if gender.lower() in ("male", "男"):
        return VOICE_PRESETS["male_young"]
    if gender.lower() in ("female", "女"):
        return VOICE_PRESETS["female_young"]
    return VOICE_PRESETS["narrator"]
