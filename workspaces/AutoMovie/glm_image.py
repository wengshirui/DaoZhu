"""
火柴人剧场 — GLM-Image 场景图生成服务
调用智谱 GLM-Image API 为每个场景生成背景插图。

失败时降级到简单模式（返回 None），不阻塞流程。
参考: Pixelle-Video services/api_media.py
"""

import logging
from pathlib import Path
from typing import Optional

import httpx

from glm_config import load_config

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def generate_scene_image(
    prompt: str,
    scene_index: int,
    size: str = "1024x1024",
) -> Optional[str]:
    """
    调用 GLM-Image 生成场景背景图。

    Args:
        prompt: 场景描述 prompt（由导演 LLM 生成）
        scene_index: 场景序号（用于命名）
        size: 图片尺寸（默认 1024x1024，GLM 要求 512-2880 且为 16 整数倍）

    Returns:
        生成的图片本地路径，失败返回 None（AC6 降级）
    """
    config = load_config()
    if not config.api_key:
        return None

    try:
        payload = {
            "model": config.image_model,
            "prompt": prompt,
        }
        # 智谱 CogView API 不需要指定 size（默认 1024x1024）
        # 如果需要其他尺寸，用 "size": "1024x1024" 格式

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{config.base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"[GLM-Image] API 返回 {resp.status_code}: "
                    f"{resp.text[:200]}"
                )
                return None

            data = resp.json()
            # 智谱 API 返回格式: {"data": [{"url": "..."}]}
            image_url = data.get("data", [{}])[0].get("url")
            if not image_url:
                logger.warning("[GLM-Image] 返回中无图片 URL")
                return None

            # 下载图片到本地
            img_resp = await client.get(image_url, timeout=30)
            if img_resp.status_code != 200:
                logger.warning(f"[GLM-Image] 图片下载失败: {img_resp.status_code}")
                return None

            filename = f"scene_{scene_index:03d}.png"
            filepath = OUTPUT_DIR / filename
            filepath.write_bytes(img_resp.content)

            logger.info(f"[GLM-Image] 场景 {scene_index} 图片生成完成: {filename}")
            return str(filepath)

    except httpx.TimeoutException:
        logger.warning(f"[GLM-Image] 场景 {scene_index} 超时")
        return None
    except Exception as e:
        logger.warning(f"[GLM-Image] 场景 {scene_index} 失败: {e}")
        return None
