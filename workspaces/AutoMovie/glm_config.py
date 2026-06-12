"""
火柴人剧场 — GLM 配置管理
工作区级别的 API Key 和模型配置。

配置存储在工作区目录下 glm_config.json（.gitignore 已排除）。
未配置时系统降级到简单模式（无声 HTML）。
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).parent / "glm_config.json"

# GLM API 默认配置
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
GLM_IMAGE_MODEL = "cogview-4"
GLM_TTS_MODEL = "glm-tts"


@dataclass
class GLMConfig:
    """GLM API 配置"""
    api_key: str = ""
    base_url: str = GLM_BASE_URL
    image_model: str = GLM_IMAGE_MODEL
    tts_model: str = GLM_TTS_MODEL
    enabled: bool = False  # 高级模式开关

    @property
    def is_ready(self) -> bool:
        """API Key 已配置且高级模式已开启"""
        return bool(self.api_key) and self.enabled


def load_config() -> GLMConfig:
    """加载 GLM 配置。文件不存在或解析失败时返回默认（未启用）。"""
    if not CONFIG_FILE.exists():
        return GLMConfig()
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return GLMConfig(
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", GLM_BASE_URL),
            image_model=data.get("image_model", GLM_IMAGE_MODEL),
            tts_model=data.get("tts_model", GLM_TTS_MODEL),
            enabled=data.get("enabled", False),
        )
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[GLM] 配置加载失败: {e}")
        return GLMConfig()


def save_config(config: GLMConfig) -> None:
    """保存 GLM 配置到文件。"""
    data = {
        "api_key": config.api_key,
        "base_url": config.base_url,
        "image_model": config.image_model,
        "tts_model": config.tts_model,
        "enabled": config.enabled,
    }
    CONFIG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("[GLM] 配置已保存")
